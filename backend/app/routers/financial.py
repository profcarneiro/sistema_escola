import calendar
import csv
import io
import json
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.financial import (
    Invoice, Payment, Expense, CostCenter,
    FormaPagamento, StatusTitulo, SituacaoDespesa, TipoCentroCusto
)
from app.models.enrollment import Matricula, StatusMatricula
from app.models.student import Aluno
from app.models.guardian import Responsavel
from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.financial import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    PaymentCreate, PaymentResponse,
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
    CostCenterCreate, CostCenterResponse,
    CostCenterReportResponse, CostCenterReportItem, CostCenterMonthMetrics,
    CashFlowSummary, DRESummary,
    DiscountsReportResponse, DiscountReportByTypeItem,
    DiscountReportByMonthItem, DiscountManualAuditItem,
)
from app.routers.auth import get_current_active_user, require_roles
from app.routers.enrollments import gerar_faturas_matricula
from app.services.cost_centers import (
    ensure_default_cost_centers,
    get_or_create_course_cost_center,
    get_general_cost_center_id,
)

router = APIRouter(prefix="/financial", tags=["Financeiro e DRE"])


def formatar_invoice_response(inv: Invoice) -> InvoiceResponse:
    resp = InvoiceResponse.model_validate(inv)
    if inv.aluno:
        resp.aluno_nome = inv.aluno.nome
    if inv.responsavel:
        resp.responsavel_nome = inv.responsavel.nome
    return resp


# ─── Títulos e Mensalidades ───────────────────────────────────────────────────

@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar título de mensalidade avulso"
)
def create_invoice(
    inv_in: InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value, UserRole.COORDENACAO.value
    ))
):
    mat = db.query(Matricula).filter(Matricula.id == inv_in.matricula_id).first()
    if not mat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(Aluno.id == inv_in.aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    resp_id = aluno.responsavel.id if aluno.responsavel else None
    valor_final = round(max(0.0, inv_in.valor_nominal - inv_in.desconto_aplicado), 2)

    curso_obj = None
    if getattr(mat, "curso_id", None):
        curso_obj = db.query(Course).filter(Course.id == mat.curso_id).first()
    elif mat.turma and mat.turma.curso_id:
        curso_obj = db.query(Course).filter(Course.id == mat.turma.curso_id).first()
    curso_id_ref = curso_obj.id if curso_obj else None
    centro_custo_id_ref = (
        get_or_create_course_cost_center(db, curso_obj).id
        if curso_obj
        else get_general_cost_center_id(db, "SEM_CENTRO")
    )

    novo_titulo = Invoice(
        matricula_id=inv_in.matricula_id,
        aluno_id=inv_in.aluno_id,
        responsavel_id=resp_id,
        curso_id=curso_id_ref,
        centro_custo_id=centro_custo_id_ref,
        descricao=inv_in.descricao.strip(),
        competencia=inv_in.competencia.strip(),
        valor_nominal=inv_in.valor_nominal,
        desconto_aplicado=inv_in.desconto_aplicado,
        valor_final=valor_final,
        data_vencimento=inv_in.data_vencimento,
        status=StatusTitulo.PENDENTE.value,
        observacoes=inv_in.observacoes
    )
    db.add(novo_titulo)
    db.commit()
    db.refresh(novo_titulo)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="TITULO_GERADO",
        entidade="Invoice",
        registro_id=str(novo_titulo.id),
        detalhes={"descricao": novo_titulo.descricao, "valor_final": novo_titulo.valor_final},
        usuario=current_user,
        ip=client_ip
    )
    return formatar_invoice_response(novo_titulo)


@router.post(
    "/invoices/generate-monthly",
    response_model=List[InvoiceResponse],
    summary="Gerar lote de faturas para todas as matrículas ativas no mês"
)
def generate_monthly_invoices(
    request: Request,
    competencia: str = Query(..., description="Ano-mês no formato YYYY-MM, ex: 2026-11"),
    dia_vencimento: int = Query(10, ge=1, le=28, description="Dia do vencimento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    ano, mes = map(int, competencia.split("-"))
    data_venc = date(ano, mes, dia_vencimento)

    matriculas_ativas = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma)
    ).filter(Matricula.status == StatusMatricula.ATIVA.value).all()

    gerados = []
    for m in matriculas_ativas:
        # Verifica se já foi gerada fatura para esta matrícula e competência
        existente = db.query(Invoice).filter(
            Invoice.matricula_id == m.id,
            Invoice.competencia == competencia
        ).first()

        if not existente:
            valor_nominal = m.valor_mensalidade
            desconto_valor = round(valor_nominal * (m.desconto_percentual / 100), 2)
            valor_final = round(valor_nominal - desconto_valor, 2)
            turma_nome = m.turma.nome if m.turma else "Arte"
            curso_obj = None
            if getattr(m, "curso_id", None):
                curso_obj = db.query(Course).filter(Course.id == m.curso_id).first()
            elif m.turma and m.turma.curso_id:
                curso_obj = db.query(Course).filter(Course.id == m.turma.curso_id).first()
            curso_id_ref = curso_obj.id if curso_obj else None
            centro_custo_id_ref = (
                get_or_create_course_cost_center(db, curso_obj).id
                if curso_obj
                else get_general_cost_center_id(db, "SEM_CENTRO")
            )

            titulo = Invoice(
                matricula_id=m.id,
                aluno_id=m.aluno_id,
                responsavel_id=m.aluno.responsavel.id if m.aluno.responsavel else None,
                curso_id=curso_id_ref,
                centro_custo_id=centro_custo_id_ref,
                descricao=f"Mensalidade {competencia} - {turma_nome}",
                competencia=competencia,
                valor_nominal=valor_nominal,
                desconto_aplicado=desconto_valor,
                valor_final=valor_final,
                data_vencimento=data_venc,
                status=StatusTitulo.PENDENTE.value
            )
            db.add(titulo)
            gerados.append(titulo)

    db.commit()
    for g in gerados:
        db.refresh(g)

    return [formatar_invoice_response(g) for g in gerados]


@router.post(
    "/invoices/sync-enrollments",
    summary="Sincronizar e gerar parcelas pendentes de todas as matrículas ativas"
)
def sync_enrollments_invoices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value, UserRole.COORDENACAO.value
    ))
):
    """Percorre todas as matrículas ativas não experimentais e gera as parcelas faltantes no Financeiro."""
    matriculas_ativas = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma)
    ).filter(
        Matricula.status == StatusMatricula.ATIVA.value,
        Matricula.aula_experimental.is_(False)
    ).all()

    total_geradas = 0
    matriculas_atualizadas = 0
    for mat in matriculas_ativas:
        novas = gerar_faturas_matricula(db, mat, aluno=mat.aluno, turma=mat.turma)
        if novas:
            total_geradas += len(novas)
            matriculas_atualizadas += 1

    if total_geradas > 0:
        db.commit()
        client_ip = request.client.host if request.client else None
        registrar_auditoria(
            db=db,
            acao="SINCRONIZACAO_PARCELAS",
            entidade="Invoice",
            registro_id="batch",
            detalhes={"matriculas_atualizadas": matriculas_atualizadas, "parcelas_geradas": total_geradas},
            usuario=current_user,
            ip=client_ip
        )

    return {
        "matriculas_processadas": len(matriculas_ativas),
        "matriculas_atualizadas": matriculas_atualizadas,
        "parcelas_geradas": total_geradas,
        "mensagem": (
            f"{total_geradas} parcela(s) gerada(s) para {matriculas_atualizadas} matrícula(s)!"
            if total_geradas > 0 else
            "Todas as matrículas ativas já possuem suas parcelas geradas."
        )
    }


@router.get("/invoices", response_model=List[InvoiceResponse], summary="Listar títulos e mensalidades")
def list_invoices(
    aluno_id: Optional[int] = Query(None, description="Filtrar por aluno"),
    responsavel_id: Optional[int] = Query(None, description="Filtrar por responsável"),
    status_filter: Optional[StatusTitulo] = Query(None, alias="status", description="Filtrar por status"),
    competencia: Optional[str] = Query(None, description="Filtrar por competência YYYY-MM"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Filtrar por mês (1-12)"),
    ano: Optional[int] = Query(None, ge=2000, le=2100, description="Filtrar por ano (YYYY)"),
    busca: Optional[str] = Query(None, description="Buscar por nome do aluno, responsável ou descrição"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Invoice).options(
        joinedload(Invoice.aluno),
        joinedload(Invoice.responsavel),
        joinedload(Invoice.pagamentos)
    )
    if aluno_id:
        query = query.filter(Invoice.aluno_id == aluno_id)
    if responsavel_id:
        query = query.filter(Invoice.responsavel_id == responsavel_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter.value)
    if competencia:
        query = query.filter(Invoice.competencia == competencia)
    if ano is not None and mes is not None:
        query = query.filter(Invoice.competencia == f"{ano:04d}-{mes:02d}")
    elif ano is not None:
        query = query.filter(Invoice.competencia.like(f"{ano:04d}-%"))
    elif mes is not None:
        query = query.filter(Invoice.competencia.like(f"%-{mes:02d}"))
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        query = query.outerjoin(Invoice.aluno).outerjoin(Invoice.responsavel).filter(
            or_(
                Invoice.descricao.ilike(termo),
                Aluno.nome.ilike(termo),
                Responsavel.nome.ilike(termo),
            )
        )

    invoices = query.order_by(Invoice.data_vencimento.asc()).all()
    today = date.today()
    status_updated = False
    for inv in invoices:
        if inv.status == StatusTitulo.PENDENTE.value and inv.data_vencimento < today:
            inv.status = StatusTitulo.ATRASADO.value
            status_updated = True

    result = [formatar_invoice_response(inv) for inv in invoices]
    if status_updated:
        db.commit()

    return result


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, summary="Obter dados do título")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    inv = db.query(Invoice).options(
        joinedload(Invoice.aluno),
        joinedload(Invoice.responsavel),
        joinedload(Invoice.pagamentos)
    ).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
    return formatar_invoice_response(inv)


# ─── Baixa de Pagamento (Formas Homologadas) ──────────────────────────────────

@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar pagamento de fatura (Baixa financeira)"
)
def pay_invoice(
    invoice_id: int,
    payment_in: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value, UserRole.COORDENACAO.value
    ))
):
    """
    Registra a liquidação financeira.
    Formas permitidas: PIX, CARTAO, BOLETO, DINHEIRO.
    """
    inv = db.query(Invoice).options(
        joinedload(Invoice.aluno),
        joinedload(Invoice.responsavel),
        joinedload(Invoice.pagamentos)
    ).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")

    if inv.status == StatusTitulo.PAGO.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este título já se encontra totalmente pago.")
    if inv.status == StatusTitulo.CANCELADO.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este título está cancelado e não pode receber baixa.")

    # Registra o pagamento
    novo_pagamento = Payment(
        invoice_id=inv.id,
        valor_pago=payment_in.valor_pago,
        forma_pagamento=payment_in.forma_pagamento.value,
        data_pagamento=datetime.now(timezone.utc),
        comprovante_transacao=payment_in.comprovante_transacao,
        recebido_por_id=current_user.id,
        observacoes=payment_in.observacoes
    )
    db.add(novo_pagamento)

    inv.status = StatusTitulo.PAGO.value
    inv.forma_pagamento = payment_in.forma_pagamento.value
    inv.data_pagamento = datetime.now(timezone.utc)

    db.commit()
    db.refresh(inv)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="PAGAMENTO_RECEBIDO",
        entidade="Invoice",
        registro_id=str(inv.id),
        detalhes={
            "valor_pago": payment_in.valor_pago,
            "forma_pagamento": payment_in.forma_pagamento.value,
            "titulo": inv.descricao
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_invoice_response(inv)


# ─── Despesas Operacionais ────────────────────────────────────────────────────

def _add_months(base_date: date, months: int) -> date:
    if months == 0:
        return base_date
    total_months = (base_date.year * 12 + (base_date.month - 1)) + months
    year, month_zero = divmod(total_months, 12)
    month = month_zero + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(base_date.day, max_day))


def _split_amount(total: float, count: int) -> List[float]:
    total_cents = round(float(total or 0.0) * 100)
    base, rem = divmod(total_cents, count)
    return [round((base + (rem if i == count - 1 else 0)) / 100.0, 2) for i in range(count)]


def _format_expense_response(exp: Expense, parcelas_criadas: int = 1) -> ExpenseResponse:
    resp = ExpenseResponse.model_validate(exp)
    if exp.centro_custo:
        resp.centro_custo_nome = exp.centro_custo.nome
    resp.parcelas_criadas = parcelas_criadas
    return resp


def _apply_expense_filters(
    query,
    categoria: Optional[str] = None,
    situacao: Optional[str] = None,
    centro_custo_id: Optional[int] = None,
    busca: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
):
    if categoria:
        query = query.filter(Expense.categoria.ilike(f"%{categoria.strip()}%"))
    if situacao:
        query = query.filter(Expense.situacao == situacao.strip().upper())
    if centro_custo_id is not None:
        query = query.filter(Expense.centro_custo_id == centro_custo_id)
    if busca:
        term = f"%{busca.strip()}%"
        query = query.filter(or_(Expense.descricao.ilike(term), Expense.categoria.ilike(term), Expense.observacoes.ilike(term)))
    if ano is not None and mes is not None:
        max_day = calendar.monthrange(ano, mes)[1]
        query = query.filter(
            Expense.data_competencia >= date(ano, mes, 1),
            Expense.data_competencia <= date(ano, mes, max_day),
        )
    elif ano is not None:
        query = query.filter(
            Expense.data_competencia >= date(ano, 1, 1),
            Expense.data_competencia <= date(ano, 12, 31),
        )
    if data_inicio:
        query = query.filter(Expense.data_competencia >= data_inicio)
    if data_fim:
        query = query.filter(Expense.data_competencia <= data_fim)
    return query


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar despesa operacional (avulsa, recorrente ou parcelada)"
)
def create_expense(
    exp_in: ExpenseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    valor_base = exp_in.valor_previsto if exp_in.valor_previsto is not None else exp_in.valor
    if valor_base is None or valor_base <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o valor previsto (ou valor) maior que zero."
        )
    valor_base = round(float(valor_base), 2)

    centro_custo_id = exp_in.centro_custo_id
    if centro_custo_id is not None:
        cc = db.query(CostCenter).filter(CostCenter.id == centro_custo_id).first()
        if not cc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centro de custo não encontrado.")
    else:
        centro_custo_id = get_general_cost_center_id(db, "SEM_CENTRO")

    if exp_in.situacao is not None:
        is_pago_inicial = exp_in.situacao == SituacaoDespesa.PAGO
    elif exp_in.pago is not None:
        is_pago_inicial = bool(exp_in.pago)
    else:
        is_pago_inicial = False

    venc_base = exp_in.data_vencimento or exp_in.data_competencia

    if exp_in.recorrente and exp_in.recorrencia_meses > 1:
        qtd = exp_in.recorrencia_meses
        valores = [valor_base] * qtd
        grupo = str(uuid.uuid4())[:12]
        eh_parcelado_ou_recorrente = True
    elif exp_in.total_parcelas > 1:
        qtd = exp_in.total_parcelas
        valores = _split_amount(valor_base, qtd)
        grupo = str(uuid.uuid4())[:12]
        eh_parcelado_ou_recorrente = True
    else:
        qtd = 1
        valores = [valor_base]
        grupo = None
        eh_parcelado_ou_recorrente = False

    criadas: List[Expense] = []
    for idx in range(qtd):
        comp_dt = _add_months(exp_in.data_competencia, idx)
        venc_dt = _add_months(venc_base, idx)
        v_prev = valores[idx]
        # Em lançamentos múltiplos (recorrentes/parcelados), apenas a 1ª herda status pago caso solicitado
        pago_item = is_pago_inicial if idx == 0 else False
        v_pago_item = (
            round(float(exp_in.valor_pago), 2)
            if (pago_item and exp_in.valor_pago is not None and exp_in.valor_pago > 0)
            else (v_prev if pago_item else 0.0)
        )
        data_pg_item = (exp_in.data_pagamento or venc_dt) if pago_item else None
        situacao_item = SituacaoDespesa.PAGO.value if pago_item else SituacaoDespesa.EM_ABERTO.value
        valor_efetivo = v_pago_item if (pago_item and v_pago_item > 0) else v_prev

        if exp_in.total_parcelas > 1 and not exp_in.recorrente:
            desc_item = f"{exp_in.descricao.strip()} ({idx + 1}/{qtd})"[:255]
        elif exp_in.recorrente and qtd > 1:
            desc_item = f"{exp_in.descricao.strip()} ({comp_dt.strftime('%m/%Y')})"[:255]
        else:
            desc_item = exp_in.descricao.strip()[:255]

        nova_despesa = Expense(
            categoria=exp_in.categoria.strip(),
            descricao=desc_item,
            valor=valor_efetivo,
            valor_previsto=v_prev,
            valor_pago=v_pago_item,
            data_competencia=comp_dt,
            data_vencimento=venc_dt,
            data_pagamento=data_pg_item,
            pago=pago_item,
            situacao=situacao_item,
            forma_pagamento=exp_in.forma_pagamento.value,
            centro_custo_id=centro_custo_id,
            recorrente=bool(exp_in.recorrente),
            parcela_atual=(idx + 1) if eh_parcelado_ou_recorrente else None,
            total_parcelas=qtd if eh_parcelado_ou_recorrente else None,
            grupo_lancamento=grupo,
            comprovante=exp_in.comprovante,
            observacoes=exp_in.observacoes,
        )
        db.add(nova_despesa)
        criadas.append(nova_despesa)

    db.commit()
    for item in criadas:
        db.refresh(item)

    first = db.query(Expense).options(joinedload(Expense.centro_custo)).filter(Expense.id == criadas[0].id).first()
    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="DESPESA_CRIADA",
        entidade="Expense",
        registro_id=str(first.id),
        detalhes={
            "categoria": first.categoria,
            "valor": first.valor,
            "parcelas_criadas": len(criadas),
        },
        usuario=current_user,
        ip=client_ip,
    )
    return _format_expense_response(first, parcelas_criadas=len(criadas))


@router.get("/expenses", response_model=List[ExpenseResponse], summary="Listar despesas operacionais")
def list_expenses(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    situacao: Optional[str] = Query(None, description="EM_ABERTO ou PAGO"),
    centro_custo_id: Optional[int] = Query(None, description="Filtrar por centro de custo"),
    busca: Optional[str] = Query(None, description="Busca em descrição, categoria ou observações"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mês de competência (1-12)"),
    ano: Optional[int] = Query(None, ge=2000, le=2100, description="Ano de competência"),
    data_inicio: Optional[date] = Query(None, description="Data início"),
    data_fim: Optional[date] = Query(None, description="Data fim"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    query = db.query(Expense).options(joinedload(Expense.centro_custo))
    query = _apply_expense_filters(
        query,
        categoria=categoria,
        situacao=situacao,
        centro_custo_id=centro_custo_id,
        busca=busca,
        mes=mes,
        ano=ano,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    rows = query.order_by(Expense.data_competencia.desc(), Expense.id.desc()).all()
    if mes is not None and ano is None:
        rows = [r for r in rows if r.data_competencia and r.data_competencia.month == mes]
    return [_format_expense_response(r) for r in rows]


@router.get("/expenses/export-csv", summary="Exportar despesas operacionais em CSV")
def export_expenses_csv(
    categoria: Optional[str] = Query(None),
    situacao: Optional[str] = Query(None),
    centro_custo_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(None),
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    query = db.query(Expense).options(joinedload(Expense.centro_custo))
    query = _apply_expense_filters(
        query,
        categoria=categoria,
        situacao=situacao,
        centro_custo_id=centro_custo_id,
        busca=busca,
        mes=mes,
        ano=ano,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    rows = query.order_by(Expense.data_competencia.desc(), Expense.id.desc()).all()
    if mes is not None and ano is None:
        rows = [r for r in rows if r.data_competencia and r.data_competencia.month == mes]

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Vencimento", "Competência", "Categoria", "Centro de Custo",
        "Descrição", "Valor Previsto", "Valor Pago", "Data Pagamento",
        "Situação", "Forma Pagamento", "Parcela", "Observações"
    ])
    for r in rows:
        parcela_txt = f"{r.parcela_atual}/{r.total_parcelas}" if r.parcela_atual and r.total_parcelas else ""
        writer.writerow([
            r.data_vencimento.strftime("%d/%m/%Y") if r.data_vencimento else "",
            r.data_competencia.strftime("%d/%m/%Y") if r.data_competencia else "",
            r.categoria,
            r.centro_custo.nome if r.centro_custo else "",
            r.descricao,
            f"{(r.valor_previsto if r.valor_previsto is not None else r.valor):.2f}".replace(".", ","),
            f"{(r.valor_pago or 0.0):.2f}".replace(".", ","),
            r.data_pagamento.strftime("%d/%m/%Y") if r.data_pagamento else "",
            r.situacao or ("PAGO" if r.pago else "EM_ABERTO"),
            r.forma_pagamento or "",
            parcela_txt,
            r.observacoes or "",
        ])

    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="despesas_escola_hb.csv"'},
    )


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse, summary="Editar ou dar baixa em despesa operacional")
def update_expense(
    expense_id: int,
    exp_in: ExpenseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    exp = db.query(Expense).filter(Expense.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despesa não encontrada.")

    if exp_in.categoria is not None:
        exp.categoria = exp_in.categoria.strip()
    if exp_in.descricao is not None:
        exp.descricao = exp_in.descricao.strip()
    if exp_in.valor_previsto is not None:
        exp.valor_previsto = round(float(exp_in.valor_previsto), 2)
    if exp_in.data_competencia is not None:
        exp.data_competencia = exp_in.data_competencia
    if exp_in.data_vencimento is not None:
        exp.data_vencimento = exp_in.data_vencimento
    if exp_in.forma_pagamento is not None:
        exp.forma_pagamento = exp_in.forma_pagamento.value
    if exp_in.centro_custo_id is not None:
        cc = db.query(CostCenter).filter(CostCenter.id == exp_in.centro_custo_id).first()
        if not cc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centro de custo não encontrado.")
        exp.centro_custo_id = exp_in.centro_custo_id
    if exp_in.comprovante is not None:
        exp.comprovante = exp_in.comprovante
    if exp_in.observacoes is not None:
        exp.observacoes = exp_in.observacoes
    if exp_in.data_pagamento is not None:
        exp.data_pagamento = exp_in.data_pagamento
    if exp_in.valor_pago is not None:
        exp.valor_pago = round(float(exp_in.valor_pago), 2)

    if exp_in.situacao is not None:
        exp.pago = exp_in.situacao == SituacaoDespesa.PAGO
        exp.situacao = exp_in.situacao.value
    elif exp_in.pago is not None:
        exp.pago = bool(exp_in.pago)
        exp.situacao = SituacaoDespesa.PAGO.value if exp.pago else SituacaoDespesa.EM_ABERTO.value

    prev_ref = exp.valor_previsto if exp.valor_previsto is not None else exp.valor
    if exp.pago:
        if not exp.valor_pago or exp.valor_pago <= 0:
            exp.valor_pago = prev_ref
        if not exp.data_pagamento:
            exp.data_pagamento = date.today()
        exp.valor = round(float(exp.valor_pago), 2)
    else:
        if exp_in.valor_pago is None:
            exp.valor_pago = 0.0
        exp.data_pagamento = None if exp_in.situacao == SituacaoDespesa.EM_ABERTO or exp_in.pago is False else exp.data_pagamento
        exp.valor = round(float(prev_ref), 2)

    db.commit()
    exp = db.query(Expense).options(joinedload(Expense.centro_custo)).filter(Expense.id == exp.id).first()

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="DESPESA_ATUALIZADA",
        entidade="Expense",
        registro_id=str(exp.id),
        detalhes={"situacao": exp.situacao, "valor": exp.valor},
        usuario=current_user,
        ip=client_ip,
    )
    return _format_expense_response(exp)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_200_OK, summary="Excluir despesa operacional")
def delete_expense(
    expense_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    exp = db.query(Expense).filter(Expense.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despesa não encontrada.")
    desc = exp.descricao
    db.delete(exp)
    db.commit()

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="DESPESA_EXCLUIDA",
        entidade="Expense",
        registro_id=str(expense_id),
        detalhes={"descricao": desc},
        usuario=current_user,
        ip=client_ip,
    )
    return {"mensagem": f"Despesa '{desc}' excluída com sucesso."}


# ─── Demonstrativos: Fluxo de Caixa e DRE ─────────────────────────────────────

@router.get("/cash-flow", response_model=CashFlowSummary, summary="Demonstrativo de Fluxo de Caixa")
def get_cash_flow(
    data_inicio: date = Query(..., description="Data inicial do período"),
    data_fim: date = Query(..., description="Data final do período"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    """Calcula entradas por forma de pagamento e saídas pagas no período."""
    pagamentos = db.query(Payment).filter(
        func.date(Payment.data_pagamento) >= data_inicio,
        func.date(Payment.data_pagamento) <= data_fim
    ).all()

    total_entradas = sum(p.valor_pago for p in pagamentos)
    entradas_por_forma: Dict[str, float] = {}
    for p in pagamentos:
        entradas_por_forma[p.forma_pagamento] = round(
            entradas_por_forma.get(p.forma_pagamento, 0.0) + p.valor_pago, 2
        )

    despesas = db.query(Expense).filter(
        Expense.pago.is_(True),
        Expense.data_pagamento >= data_inicio,
        Expense.data_pagamento <= data_fim
    ).all()

    total_saidas = 0.0
    saidas_por_categoria: Dict[str, float] = {}
    for d in despesas:
        val = float(d.valor_pago if (d.valor_pago and d.valor_pago > 0) else d.valor)
        total_saidas += val
        saidas_por_categoria[d.categoria] = round(
            saidas_por_categoria.get(d.categoria, 0.0) + val, 2
        )

    return CashFlowSummary(
        periodo_inicio=data_inicio,
        periodo_fim=data_fim,
        total_entradas=round(total_entradas, 2),
        total_saidas=round(total_saidas, 2),
        saldo_operacional=round(total_entradas - total_saidas, 2),
        entradas_por_forma=entradas_por_forma,
        saidas_por_categoria=saidas_por_categoria
    )


@router.get("/dre", response_model=DRESummary, summary="DRE - Demonstração do Resultado do Exercício")
def get_dre(
    competencia_inicio: date = Query(..., description="Data inicial de competência"),
    competencia_fim: date = Query(..., description="Data final de competência"),
    aluno_id: Optional[int] = Query(None, description="Filtrar receitas do DRE por aluno específico"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    """
    DRE Operacional da Escola:
    (+) Receita Bruta (Valor Nominal Faturado)
    (-) Deduções e Descontos Concedidos
    (=) Receita Líquida
    (-) Despesas Operacionais
    (=) Resultado Líquido do Período
    """
    faturas_query = db.query(Invoice).filter(
        Invoice.data_vencimento >= competencia_inicio,
        Invoice.data_vencimento <= competencia_fim,
        Invoice.status != StatusTitulo.CANCELADO.value
    )
    if aluno_id is not None:
        faturas_query = faturas_query.filter(Invoice.aluno_id == aluno_id)
    faturas = faturas_query.all()

    receita_bruta = sum((f.valor_nominal or 0.0) + (f.juros_multa or 0.0) for f in faturas)
    deducoes_descontos = sum(f.desconto_aplicado or 0.0 for f in faturas)
    receita_liquida = round(receita_bruta - deducoes_descontos, 2)

    despesas = [] if aluno_id is not None else db.query(Expense).filter(
        Expense.data_competencia >= competencia_inicio,
        Expense.data_competencia <= competencia_fim
    ).all()

    total_despesas = sum(d.valor for d in despesas)
    despesas_discriminadas: Dict[str, float] = {}
    for d in despesas:
        despesas_discriminadas[d.categoria] = round(
            despesas_discriminadas.get(d.categoria, 0.0) + d.valor, 2
        )

    resultado_liquido = round(receita_liquida - total_despesas, 2)

    return DRESummary(
        competencia_inicio=competencia_inicio,
        competencia_fim=competencia_fim,
        receita_bruta=round(receita_bruta, 2),
        deducoes_descontos=round(deducoes_descontos, 2),
        receita_liquida=round(receita_liquida, 2),
        despesas_operacionais=round(total_despesas, 2),
        resultado_liquido=resultado_liquido,
        despesas_discriminadas=despesas_discriminadas
    )


@router.get("/discounts-report", response_model=DiscountsReportResponse, summary="Relatório de descontos concedidos por tipo e por mês")
def get_discounts_report(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    competencia_inicio: Optional[str] = Query(None, description="YYYY-MM"),
    competencia_fim: Optional[str] = Query(None, description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value)),
):
    query = db.query(Invoice).options(
        joinedload(Invoice.matricula).joinedload(Matricula.aluno),
        joinedload(Invoice.matricula).joinedload(Matricula.turma),
    ).filter(Invoice.status != StatusTitulo.CANCELADO.value)

    if ano is not None and mes is not None:
        query = query.filter(Invoice.competencia == f"{ano:04d}-{mes:02d}")
    elif ano is not None:
        query = query.filter(Invoice.competencia.like(f"{ano:04d}-%"))
    elif mes is not None:
        query = query.filter(Invoice.competencia.like(f"%-{mes:02d}"))
    if competencia_inicio:
        query = query.filter(Invoice.competencia >= competencia_inicio)
    if competencia_fim:
        query = query.filter(Invoice.competencia <= competencia_fim)

    faturas = query.all()

    total_descontos = 0.0
    total_faturas_com_desconto = 0
    por_tipo_map: Dict[str, Dict] = {}
    por_mes_map: Dict[str, Dict] = {}
    manual_mats: Dict[int, Matricula] = {}

    for inv in faturas:
        desc_val = round(float(inv.desconto_aplicado or 0.0), 2)
        nom_val = round(float(inv.valor_nominal or 0.0), 2)
        liq_val = round(float(inv.valor_final or 0.0), 2)

        mes_entry = por_mes_map.setdefault(inv.competencia, {
            "competencia": inv.competencia,
            "quantidade_faturas": 0,
            "total_bruto": 0.0,
            "total_desconto": 0.0,
            "total_liquido": 0.0,
        })
        mes_entry["total_bruto"] = round(mes_entry["total_bruto"] + nom_val, 2)
        mes_entry["total_liquido"] = round(mes_entry["total_liquido"] + liq_val, 2)

        mat = inv.matricula
        if mat and mat.desconto_editado_manualmente:
            manual_mats[mat.id] = mat

        if desc_val <= 0.0:
            continue

        total_descontos = round(total_descontos + desc_val, 2)
        total_faturas_com_desconto += 1
        mes_entry["quantidade_faturas"] += 1
        mes_entry["total_desconto"] = round(mes_entry["total_desconto"] + desc_val, 2)

        # Determina rótulo(s) do tipo de desconto a partir do snapshot da matrícula
        tipos_rotulos: List[str] = []
        if mat:
            if mat.descontos_aplicados_json:
                try:
                    itens = json.loads(mat.descontos_aplicados_json)
                    for it in itens:
                        if it.get("nome") and float(it.get("percentual") or 0.0) > 0:
                            tipos_rotulos.append(it["nome"])
                except Exception:
                    pass
            if not tipos_rotulos and mat.plano_nome and float(mat.desconto_plano_percentual or 0.0) > 0:
                tipos_rotulos.append(mat.plano_nome)
            if not tipos_rotulos and mat.tipo_desconto:
                tipos_rotulos.append(mat.tipo_desconto.capitalize())
            if float(mat.desconto_valor_fixo or 0.0) > 0 and "Desconto em R$" not in tipos_rotulos:
                if not tipos_rotulos:
                    tipos_rotulos.append("Desconto em R$")
            if mat.desconto_editado_manualmente and not tipos_rotulos:
                tipos_rotulos.append("Manual")
        if not tipos_rotulos:
            tipos_rotulos = ["Outros"]

        tipo_chave = " + ".join(tipos_rotulos)
        t_entry = por_tipo_map.setdefault(tipo_chave, {
            "tipo": tipo_chave,
            "quantidade_faturas": 0,
            "matriculas_ids": set(),
            "total_desconto": 0.0,
        })
        t_entry["quantidade_faturas"] += 1
        if mat:
            t_entry["matriculas_ids"].add(mat.id)
        t_entry["total_desconto"] = round(t_entry["total_desconto"] + desc_val, 2)

    por_tipo = [
        DiscountReportByTypeItem(
            tipo=v["tipo"],
            quantidade_faturas=v["quantidade_faturas"],
            quantidade_matriculas=len(v["matriculas_ids"]),
            total_desconto=v["total_desconto"],
        )
        for v in sorted(por_tipo_map.values(), key=lambda x: x["total_desconto"], reverse=True)
    ]

    por_mes = [
        DiscountReportByMonthItem(**v)
        for v in sorted(por_mes_map.values(), key=lambda x: x["competencia"])
        if v["total_desconto"] > 0 or v["quantidade_faturas"] > 0
    ]

    alteracoes_manuais = [
        DiscountManualAuditItem(
            matricula_id=m.id,
            aluno_nome=m.aluno.nome if m.aluno else f"Aluno #{m.aluno_id}",
            turma_nome=m.turma.nome if m.turma else f"Turma #{m.turma_id}",
            plano_nome=m.plano_nome,
            desconto_percentual=float(m.desconto_percentual or 0.0),
            desconto_valor_fixo=float(m.desconto_valor_fixo or 0.0),
            alterado_por=m.desconto_alterado_por_nome,
            motivo=m.desconto_motivo_alteracao,
            alterado_em=m.desconto_alterado_em,
        )
        for m in sorted(manual_mats.values(), key=lambda x: x.id, reverse=True)
    ]

    return DiscountsReportResponse(
        total_descontos_concedidos=total_descontos,
        total_faturas_com_desconto=total_faturas_com_desconto,
        por_tipo=por_tipo,
        por_mes=por_mes,
        alteracoes_manuais=alteracoes_manuais,
    )


# ─── Régua de Cobrança e Inadimplência ─────────────────────────────────────────

@router.get("/defaulters", response_model=List[InvoiceResponse], summary="Régua de cobrança - Inadimplentes")
def list_defaulters(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value, UserRole.COORDENACAO.value
    ))
):
    """
    Identifica títulos vencidos e não pagos, atualizando status para ATRASADO
    e calculando multa contratual (2%) e juros (1% a.m.).
    """
    hoje = date.today()
    inadimplentes = db.query(Invoice).options(
        joinedload(Invoice.aluno),
        joinedload(Invoice.responsavel)
    ).filter(
        Invoice.status.in_([StatusTitulo.PENDENTE.value, StatusTitulo.ATRASADO.value]),
        Invoice.data_vencimento < hoje
    ).all()

    for inv in inadimplentes:
        inv.status = StatusTitulo.ATRASADO.value
        dias_atraso = (hoje - inv.data_vencimento).days
        multa = inv.valor_nominal * 0.02  # 2% de multa contratual
        juros = inv.valor_nominal * (0.01 / 30) * dias_atraso  # 1% a.m. pro-rata
        inv.juros_multa = round(multa + juros, 2)
        inv.valor_final = round(inv.valor_nominal - inv.desconto_aplicado + inv.juros_multa, 2)

    db.commit()
    for inv in inadimplentes:
        db.refresh(inv)

    return [formatar_invoice_response(inv) for inv in inadimplentes]


# ─── Centros de Custo e Relatório Gerencial ──────────────────────────────────

@router.get("/cost-centers", response_model=List[CostCenterResponse], summary="Listar centros de custo gerais e por curso")
def list_cost_centers(
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    ensure_default_cost_centers(db)
    query = db.query(CostCenter)
    if apenas_ativos:
        query = query.filter(CostCenter.ativo.is_(True))
    return query.order_by(CostCenter.tipo.asc(), CostCenter.nome.asc()).all()


@router.post("/cost-centers", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED, summary="Criar centro de custo adicional")
def create_cost_center(
    cc_in: CostCenterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    nome_clean = cc_in.nome.strip()
    codigo = (cc_in.codigo or nome_clean.upper().replace(" ", "_"))[:60]
    existing = db.query(CostCenter).filter(or_(CostCenter.codigo == codigo, CostCenter.nome.ilike(nome_clean))).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um centro de custo com esse código ou nome.")
    novo = CostCenter(
        codigo=codigo,
        nome=nome_clean,
        tipo=cc_in.tipo.value,
        curso_id=cc_in.curso_id,
        ativo=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.get("/cost-centers/report", response_model=CostCenterReportResponse, summary="Relatório de receitas, custos e resultado por centro de custo mês a mês")
def get_cost_centers_report(
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    mes: Optional[int] = Query(None, ge=1, le=12),
    competencia_inicio: Optional[str] = Query(None, description="YYYY-MM"),
    competencia_fim: Optional[str] = Query(None, description="YYYY-MM"),
    tipo: Optional[str] = Query(None, description="Filtrar por GERAL ou CURSO"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    ensure_default_cost_centers(db)
    centros = db.query(CostCenter).order_by(CostCenter.tipo.asc(), CostCenter.nome.asc()).all()
    if tipo:
        centros = [c for c in centros if c.tipo == tipo.upper()]

    sem_centro_id = get_general_cost_center_id(db, "SEM_CENTRO")
    cc_by_id: Dict[int, CostCenter] = {c.id: c for c in centros}

    # Mapear curso_id -> centro_custo_id para faturas antigas sem centro preenchido
    cc_by_course: Dict[int, int] = {c.curso_id: c.id for c in centros if c.curso_id}

    inv_query = db.query(Invoice).options(
        joinedload(Invoice.pagamentos),
        joinedload(Invoice.matricula).joinedload(Matricula.turma),
    ).filter(Invoice.status != StatusTitulo.CANCELADO.value)

    if ano is not None and mes is not None:
        inv_query = inv_query.filter(Invoice.competencia == f"{ano:04d}-{mes:02d}")
    elif ano is not None:
        inv_query = inv_query.filter(Invoice.competencia.like(f"{ano:04d}-%"))
    elif mes is not None:
        inv_query = inv_query.filter(Invoice.competencia.like(f"%-{mes:02d}"))
    if competencia_inicio:
        inv_query = inv_query.filter(Invoice.competencia >= competencia_inicio)
    if competencia_fim:
        inv_query = inv_query.filter(Invoice.competencia <= competencia_fim)

    faturas = inv_query.all()

    exp_query = db.query(Expense)
    if ano is not None and mes is not None:
        max_d = calendar.monthrange(ano, mes)[1]
        exp_query = exp_query.filter(Expense.data_competencia >= date(ano, mes, 1), Expense.data_competencia <= date(ano, mes, max_d))
    elif ano is not None:
        exp_query = exp_query.filter(Expense.data_competencia >= date(ano, 1, 1), Expense.data_competencia <= date(ano, 12, 31))
    despesas = exp_query.all()
    if mes is not None and ano is None:
        despesas = [d for d in despesas if d.data_competencia and d.data_competencia.month == mes]
    if competencia_inicio:
        despesas = [d for d in despesas if d.data_competencia and d.data_competencia.strftime("%Y-%m") >= competencia_inicio]
    if competencia_fim:
        despesas = [d for d in despesas if d.data_competencia and d.data_competencia.strftime("%Y-%m") <= competencia_fim]

    # Estrutura agregadora: cc_id -> comp -> metricas
    agg: Dict[int, Dict[str, Dict[str, float]]] = {c.id: {} for c in centros}

    def _slot(cc_id: int, comp: str) -> Optional[Dict[str, float]]:
        if cc_id not in agg:
            return None
        return agg[cc_id].setdefault(comp, {
            "rec_prev": 0.0,
            "cus_prev": 0.0,
            "rec_real": 0.0,
            "cus_real": 0.0,
        })

    for inv in faturas:
        cc_id = inv.centro_custo_id
        if not cc_id:
            cid = inv.curso_id or (inv.matricula.curso_id if inv.matricula else None) or (inv.matricula.turma.curso_id if inv.matricula and inv.matricula.turma else None)
            cc_id = cc_by_course.get(cid) if cid else None
        if not cc_id:
            cc_id = sem_centro_id
        if cc_id not in cc_by_id:
            continue
        slot = _slot(cc_id, inv.competencia)
        if slot is None:
            continue
        rec_prev = round(float(inv.valor_final or 0.0), 2)
        if inv.pagamentos:
            rec_real = round(sum(float(p.valor_pago or 0.0) for p in inv.pagamentos), 2)
        elif inv.status == StatusTitulo.PAGO.value:
            rec_real = rec_prev
        else:
            rec_real = 0.0
        slot["rec_prev"] += rec_prev
        slot["rec_real"] += rec_real

    for d in despesas:
        cc_id = d.centro_custo_id or sem_centro_id
        if cc_id not in cc_by_id:
            continue
        comp = d.data_competencia.strftime("%Y-%m")
        slot = _slot(cc_id, comp)
        if slot is None:
            continue
        cus_prev = round(float(d.valor_previsto if d.valor_previsto is not None else d.valor or 0.0), 2)
        cus_real = round(float(d.valor_pago if (d.pago and d.valor_pago and d.valor_pago > 0) else (d.valor if d.pago else 0.0)), 2)
        slot["cus_prev"] += cus_prev
        slot["cus_real"] += cus_real

    total_rec_prev = sum(v["rec_prev"] for m in agg.values() for v in m.values())
    total_cus_prev = sum(v["cus_prev"] for m in agg.values() for v in m.values())
    total_rec_real = sum(v["rec_real"] for m in agg.values() for v in m.values())
    total_cus_real = sum(v["cus_real"] for m in agg.values() for v in m.values())

    itens: List[CostCenterReportItem] = []
    for c in centros:
        meses_map = agg.get(c.id, {})
        meses_list = [
            CostCenterMonthMetrics(
                competencia=comp,
                receita_prevista=round(vals["rec_prev"], 2),
                custo_previsto=round(vals["cus_prev"], 2),
                resultado_previsto=round(vals["rec_prev"] - vals["cus_prev"], 2),
                receita_realizada=round(vals["rec_real"], 2),
                custo_realizado=round(vals["cus_real"], 2),
                resultado_realizado=round(vals["rec_real"] - vals["cus_real"], 2),
            )
            for comp, vals in sorted(meses_map.items())
        ]
        rp = round(sum(m.receita_prevista for m in meses_list), 2)
        cp = round(sum(m.custo_previsto for m in meses_list), 2)
        rr = round(sum(m.receita_realizada for m in meses_list), 2)
        cr = round(sum(m.custo_realizado for m in meses_list), 2)

        itens.append(CostCenterReportItem(
            centro_custo_id=c.id,
            nome=c.nome,
            tipo=c.tipo,
            curso_id=c.curso_id,
            receita_prevista_total=rp,
            custo_previsto_total=cp,
            resultado_previsto_total=round(rp - cp, 2),
            percentual_receita_prevista=round((rp / total_rec_prev) * 100, 2) if total_rec_prev > 0 else 0.0,
            receita_realizada_total=rr,
            custo_realizado_total=cr,
            resultado_realizado_total=round(rr - cr, 2),
            percentual_receita_realizada=round((rr / total_rec_real) * 100, 2) if total_rec_real > 0 else 0.0,
            meses=meses_list,
        ))

    return CostCenterReportResponse(
        total_receita_prevista=round(total_rec_prev, 2),
        total_custo_previsto=round(total_cus_prev, 2),
        total_resultado_previsto=round(total_rec_prev - total_cus_prev, 2),
        total_receita_realizada=round(total_rec_real, 2),
        total_custo_realizado=round(total_cus_real, 2),
        total_resultado_realizado=round(total_rec_real - total_cus_real, 2),
        centros=itens,
    )
