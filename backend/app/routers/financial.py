from datetime import date, datetime, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.financial import (
    Invoice, Payment, Expense,
    FormaPagamento, StatusTitulo
)
from app.models.enrollment import Matricula, StatusMatricula
from app.models.student import Aluno
from app.models.guardian import Responsavel
from app.models.user import User, UserRole
from app.schemas.financial import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    PaymentCreate, PaymentResponse,
    ExpenseCreate, ExpenseResponse,
    CashFlowSummary, DRESummary
)
from app.routers.auth import get_current_active_user, require_roles

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

    novo_titulo = Invoice(
        matricula_id=inv_in.matricula_id,
        aluno_id=inv_in.aluno_id,
        responsavel_id=resp_id,
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

            titulo = Invoice(
                matricula_id=m.id,
                aluno_id=m.aluno_id,
                responsavel_id=m.aluno.responsavel.id if m.aluno.responsavel else None,
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


@router.get("/invoices", response_model=List[InvoiceResponse], summary="Listar títulos e mensalidades")
def list_invoices(
    aluno_id: Optional[int] = Query(None, description="Filtrar por aluno"),
    status_filter: Optional[StatusTitulo] = Query(None, alias="status", description="Filtrar por status"),
    competencia: Optional[str] = Query(None, description="Filtrar por competência YYYY-MM"),
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
    if status_filter:
        query = query.filter(Invoice.status == status_filter.value)
    if competencia:
        query = query.filter(Invoice.competencia == competencia)

    invoices = query.order_by(Invoice.data_vencimento.asc()).all()
    today = date.today()
    status_updated = False
    for inv in invoices:
        if inv.status == StatusTitulo.PENDENTE.value and inv.data_vencimento < today:
            inv.status = StatusTitulo.ATRASADO.value
            status_updated = True
    if status_updated:
        db.commit()

    return [formatar_invoice_response(inv) for inv in invoices]


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

@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar despesa operacional"
)
def create_expense(
    exp_in: ExpenseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    nova_despesa = Expense(
        categoria=exp_in.categoria.strip(),
        descricao=exp_in.descricao.strip(),
        valor=exp_in.valor,
        data_competencia=exp_in.data_competencia,
        data_pagamento=exp_in.data_pagamento,
        pago=exp_in.pago,
        forma_pagamento=exp_in.forma_pagamento.value,
        comprovante=exp_in.comprovante,
        observacoes=exp_in.observacoes
    )
    db.add(nova_despesa)
    db.commit()
    db.refresh(nova_despesa)
    return nova_despesa


@router.get("/expenses", response_model=List[ExpenseResponse], summary="Listar despesas operacionais")
def list_expenses(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    data_inicio: Optional[date] = Query(None, description="Data início"),
    data_fim: Optional[date] = Query(None, description="Data fim"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    query = db.query(Expense)
    if categoria:
        query = query.filter(Expense.categoria.ilike(f"%{categoria.strip()}%"))
    if data_inicio:
        query = query.filter(Expense.data_competencia >= data_inicio)
    if data_fim:
        query = query.filter(Expense.data_competencia <= data_fim)
    return query.order_by(Expense.data_competencia.desc()).all()


# ─── Demonstrativos: Fluxo de Caixa e DRE ─────────────────────────────────────

@router.get("/cash-flow", response_model=CashFlowSummary, summary="Demonstrativo de Fluxo de Caixa")
def get_cash_flow(
    data_inicio: date = Query(..., description="Data inicial do período"),
    data_fim: date = Query(..., description="Data final do período"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    """Calcula entradas por forma de pagamento e saídas pagas no período."""
    # Entradas (pagamentos efetuados)
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

    # Saídas (despesas pagas)
    despesas = db.query(Expense).filter(
        Expense.pago.is_(True),
        Expense.data_pagamento >= data_inicio,
        Expense.data_pagamento <= data_fim
    ).all()

    total_saidas = sum(d.valor for d in despesas)
    saidas_por_categoria: Dict[str, float] = {}
    for d in despesas:
        saidas_por_categoria[d.categoria] = round(
            saidas_por_categoria.get(d.categoria, 0.0) + d.valor, 2
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
    faturas = db.query(Invoice).filter(
        Invoice.data_vencimento >= competencia_inicio,
        Invoice.data_vencimento <= competencia_fim,
        Invoice.status != StatusTitulo.CANCELADO.value
    ).all()

    receita_bruta = sum(f.valor_nominal for f in faturas)
    deducoes_descontos = sum(f.desconto_aplicado for f in faturas)
    receita_liquida = sum(f.valor_final for f in faturas)

    despesas = db.query(Expense).filter(
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
