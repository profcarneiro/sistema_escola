import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import calendar
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Invoice, StatusTitulo
from app.models.waitlist import ListaEspera
from app.models.student import Aluno
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.discount_policy import CondicaoPagamento
from app.models.user import User, UserRole
from app.schemas.enrollment import (
    MatriculaCreate, MatriculaUpdate, MatriculaResponse,
    ListaEsperaCreate, ListaEsperaResponse
)
from app.routers.auth import get_current_active_user, require_roles
from app.services.discount_policy import simular_politica_desconto
from app.services.cost_centers import get_or_create_course_cost_center, get_general_cost_center_id

router = APIRouter(prefix="/enrollments", tags=["Matrículas e Lista de Espera"])


def _split_amount(total: float, count: int) -> List[float]:
    """Divide um valor monetário em N parcelas exatas sem perda de centavos."""
    if count <= 0:
        return []
    total_cents = round(float(total or 0.0) * 100)
    base, rem = divmod(total_cents, count)
    return [
        round((base + (rem if i == count - 1 else 0)) / 100.0, 2)
        for i in range(count)
    ]


def contar_matriculas_ativas(db: Session, turma_id: int) -> int:
    """Conta alunos matriculados e ativos em uma turma."""
    return db.query(Matricula).filter(
        Matricula.turma_id == turma_id,
        Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value])
    ).count()


def contar_parcelas_matricula(db: Session, matricula_id: int) -> int:
    """Conta títulos não cancelados vinculados a uma matrícula."""
    return db.query(Invoice).filter(
        Invoice.matricula_id == matricula_id,
        Invoice.status != StatusTitulo.CANCELADO.value
    ).count()


STATUS_FATURAS_ABERTAS = (StatusTitulo.PENDENTE.value, StatusTitulo.ATRASADO.value)


def _cancelar_faturas_abertas(faturas: List[Invoice], motivo: str) -> int:
    """Cancela apenas títulos ainda em aberto, preservando títulos já pagos."""
    canceladas = 0
    for inv in faturas:
        if inv.status in STATUS_FATURAS_ABERTAS:
            inv.status = StatusTitulo.CANCELADO.value
            inv.observacoes = f"{inv.observacoes} | {motivo}".strip(" |") if inv.observacoes else motivo
            canceladas += 1
    return canceladas


def sincronizar_faturas_matricula(
    db: Session,
    matricula: Matricula,
    aluno: Optional[Aluno] = None,
    turma: Optional[ClassGroup] = None
) -> Dict[str, Any]:
    """
    Sincroniza todas as faturas da matrícula no Financeiro conforme duração e condição de pagamento:
    - Matrícula CANCELADA, EXPERIMENTAL ou CORTESIA: cancela parcelas em aberto, preservando PAGO.
    - Matrícula TRANCADA: cancela parcelas futuras (PENDENTE).
    - Matrícula ATIVA: gera/atualiza cobranças para A_VISTA (1x), PARCELADO (1x..12x) ou MENSAL (N meses).
    """
    faturas_nao_canceladas = db.query(Invoice).filter(
        Invoice.matricula_id == matricula.id,
        Invoice.status != StatusTitulo.CANCELADO.value
    ).order_by(Invoice.competencia.asc(), Invoice.id.asc()).all()

    if matricula.status == StatusMatricula.CANCELADA.value:
        motivo = matricula.motivo_cancelamento or "Matrícula cancelada"
        canceladas = _cancelar_faturas_abertas(faturas_nao_canceladas, f"Cancelado: {motivo}")
        return {"geradas": [], "atualizadas": 0, "canceladas": canceladas}

    if matricula.status == StatusMatricula.EXPERIMENTAL.value or matricula.aula_experimental:
        canceladas = _cancelar_faturas_abertas(faturas_nao_canceladas, "Matrícula convertida para aula experimental")
        return {"geradas": [], "atualizadas": 0, "canceladas": canceladas}

    if getattr(matricula, "is_cortesia", False):
        canceladas = _cancelar_faturas_abertas(
            faturas_nao_canceladas,
            f"Matrícula cortesia ({matricula.tipo_cortesia or 'sem cobrança'})"
        )
        return {"geradas": [], "atualizadas": 0, "canceladas": canceladas}

    if matricula.status == StatusMatricula.TRANCADA.value:
        canceladas = _cancelar_faturas_abertas(
            [inv for inv in faturas_nao_canceladas if inv.status == StatusTitulo.PENDENTE.value],
            "Matrícula trancada"
        )
        return {"geradas": [], "atualizadas": 0, "canceladas": canceladas}

    if matricula.status != StatusMatricula.ATIVA.value:
        return {"geradas": [], "atualizadas": 0, "canceladas": 0}

    condicao = getattr(matricula, "condicao_pagamento", None) or CondicaoPagamento.MENSAL.value
    duracao_meses = max(1, int(getattr(matricula, "duracao_contrato_meses", None) or matricula.quantidade_parcelas or 12))
    if condicao == CondicaoPagamento.A_VISTA.value:
        quantidade_cobrancas = 1
    elif condicao == CondicaoPagamento.PARCELADO.value:
        quantidade_cobrancas = min(12, max(1, int(matricula.quantidade_parcelas or 1)))
    else:
        quantidade_cobrancas = duracao_meses

    dia_vencimento = matricula.dia_vencimento or 10

    if aluno is None:
        aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(Aluno.id == matricula.aluno_id).first()
    if turma is None:
        turma = db.query(ClassGroup).filter(ClassGroup.id == matricula.turma_id).first()

    curso_obj = None
    if getattr(matricula, "curso_id", None):
        curso_obj = getattr(matricula, "curso", None) or db.query(Course).filter(Course.id == matricula.curso_id).first()
    elif turma and turma.curso_id:
        curso_obj = db.query(Course).filter(Course.id == turma.curso_id).first()

    curso_nome = curso_obj.nome if curso_obj else None
    curso_id_ref = curso_obj.id if curso_obj else None
    centro_custo_id_ref = (
        get_or_create_course_cost_center(db, curso_obj).id
        if curso_obj
        else get_general_cost_center_id(db, "SEM_CENTRO")
    )

    turma_nome = turma.nome if turma else f"Turma #{matricula.turma_id}"
    label_servico = curso_nome or turma_nome

    valor_mensal = round(float(matricula.valor_mensalidade or 0.0), 2)
    valor_total_bruto = round(
        float(matricula.valor_total_contrato)
        if getattr(matricula, "valor_total_contrato", None) is not None
        else (valor_mensal * duracao_meses),
        2
    )
    desconto_pct = float(matricula.desconto_percentual or 0.0)
    desconto_fixo = max(0.0, float(getattr(matricula, "desconto_valor_fixo", 0.0) or 0.0))
    desconto_total = min(
        valor_total_bruto,
        round(round(valor_total_bruto * (desconto_pct / 100.0), 2) + desconto_fixo, 2)
    )

    nominais_por_slot = _split_amount(valor_total_bruto, quantidade_cobrancas)
    descontos_por_slot = _split_amount(desconto_total, quantidade_cobrancas)

    if desconto_pct > 0 and desconto_fixo > 0:
        desc_sufixo = f" (desconto {desconto_pct:g}% + R$ {desconto_fixo:.2f})"
    elif desconto_pct > 0:
        desc_sufixo = f" (desconto {desconto_pct:g}%)"
    elif desconto_fixo > 0:
        desc_sufixo = f" (desconto R$ {desconto_fixo:.2f})"
    else:
        desc_sufixo = ""

    slots = []
    ano_cursor = matricula.data_inicio.year
    mes_cursor = matricula.data_inicio.month
    for i in range(quantidade_cobrancas):
        max_dias = calendar.monthrange(ano_cursor, mes_cursor)[1]
        dia_efetivo = min(dia_vencimento, max_dias)
        data_venc = date(ano_cursor, mes_cursor, dia_efetivo)
        competencia = f"{ano_cursor:04d}-{mes_cursor:02d}"
        nom_slot = nominais_por_slot[i]
        desc_slot = min(nom_slot, descontos_por_slot[i])
        final_slot = round(max(0.0, nom_slot - desc_slot), 2)

        if condicao == CondicaoPagamento.A_VISTA.value:
            descricao_slot = f"À vista - {label_servico}{desc_sufixo}"[:200]
        elif condicao == CondicaoPagamento.PARCELADO.value:
            descricao_slot = f"Parcela {i + 1}/{quantidade_cobrancas} - {label_servico} (parcelado){desc_sufixo}"[:200]
        else:
            descricao_slot = f"Mensalidade {i + 1}/{quantidade_cobrancas} ({mes_cursor:02d}/{ano_cursor}) - {label_servico} (mensal){desc_sufixo}"[:200]

        slots.append({
            "indice": i + 1,
            "competencia": competencia,
            "data_vencimento": data_venc,
            "valor_nominal": nom_slot,
            "desconto_aplicado": desc_slot,
            "valor_final": final_slot,
            "descricao": descricao_slot,
        })
        mes_cursor += 1
        if mes_cursor > 12:
            mes_cursor = 1
            ano_cursor += 1

    target_competencias = {slot["competencia"] for slot in slots}

    faturas_por_competencia: Dict[str, List[Invoice]] = {}
    faturas_fora_da_grade: List[Invoice] = []
    for inv in faturas_nao_canceladas:
        if inv.competencia in target_competencias:
            faturas_por_competencia.setdefault(inv.competencia, []).append(inv)
        else:
            faturas_fora_da_grade.append(inv)

    canceladas = _cancelar_faturas_abertas(
        faturas_fora_da_grade,
        f"Ajuste de cobranças da matrícula ({quantidade_cobrancas}x)"
    )

    hoje = date.today()
    resp_id = aluno.responsavel.id if aluno and aluno.responsavel else None
    novas_faturas: List[Invoice] = []
    atualizadas = 0

    for slot in slots:
        competencia = slot["competencia"]
        data_venc = slot["data_vencimento"]
        status_esperado = StatusTitulo.ATRASADO.value if data_venc < hoje else StatusTitulo.PENDENTE.value
        desc = slot["descricao"]
        valor_nominal = slot["valor_nominal"]
        desconto_val = slot["desconto_aplicado"]
        valor_final = slot["valor_final"]

        existentes = faturas_por_competencia.get(competencia, [])
        if existentes:
            existentes.sort(key=lambda f: (0 if f.status == StatusTitulo.PAGO.value else 1, f.id))
            principal = existentes[0]
            if len(existentes) > 1:
                canceladas += _cancelar_faturas_abertas(existentes[1:], "Ajuste de parcelas duplicadas")

            if principal.status in STATUS_FATURAS_ABERTAS:
                alterou = (
                    principal.descricao != desc
                    or round(float(principal.valor_nominal or 0.0), 2) != valor_nominal
                    or round(float(principal.desconto_aplicado or 0.0), 2) != desconto_val
                    or round(float(principal.valor_final or 0.0), 2) != valor_final
                    or principal.data_vencimento != data_venc
                    or principal.status != status_esperado
                    or principal.responsavel_id != resp_id
                    or principal.curso_id != curso_id_ref
                    or principal.centro_custo_id != centro_custo_id_ref
                )
                if alterou:
                    principal.descricao = desc
                    principal.valor_nominal = valor_nominal
                    principal.desconto_aplicado = desconto_val
                    principal.valor_final = valor_final
                    principal.data_vencimento = data_venc
                    principal.status = status_esperado
                    principal.responsavel_id = resp_id
                    principal.curso_id = curso_id_ref
                    principal.centro_custo_id = centro_custo_id_ref
                    atualizadas += 1
            continue

        fatura = Invoice(
            matricula_id=matricula.id,
            aluno_id=matricula.aluno_id,
            responsavel_id=resp_id,
            curso_id=curso_id_ref,
            centro_custo_id=centro_custo_id_ref,
            descricao=desc,
            competencia=competencia,
            valor_nominal=valor_nominal,
            desconto_aplicado=desconto_val,
            valor_final=valor_final,
            data_vencimento=data_venc,
            status=status_esperado
        )
        db.add(fatura)
        novas_faturas.append(fatura)

    return {"geradas": novas_faturas, "atualizadas": atualizadas, "canceladas": canceladas}


def gerar_faturas_matricula(
    db: Session,
    matricula: Matricula,
    aluno: Optional[Aluno] = None,
    turma: Optional[ClassGroup] = None
) -> List[Invoice]:
    """Gera e sincroniza automaticamente as mensalidades da matrícula ativa no Financeiro."""
    return sincronizar_faturas_matricula(db, matricula, aluno=aluno, turma=turma)["geradas"]


def formatar_matricula_response(matricula: Matricula, total_parcelas: int = 0) -> MatriculaResponse:
    resp = MatriculaResponse.model_validate(matricula)
    if matricula.aluno:
        resp.aluno_nome = matricula.aluno.nome
    if matricula.turma:
        resp.turma_nome = matricula.turma.nome
    if matricula.curso:
        resp.curso_nome = matricula.curso.nome
    elif matricula.turma and matricula.turma.curso:
        resp.curso_nome = matricula.turma.curso.nome

    if matricula.descontos_aplicados_json:
        try:
            itens = json.loads(matricula.descontos_aplicados_json)
            resp.descontos_aplicados = itens
            resp.descontos_ids = [int(it["id"]) for it in itens if it.get("id") and it.get("tipo") == "DESCONTO"]
        except Exception:
            resp.descontos_aplicados = []

    duracao = max(1, int(matricula.duracao_contrato_meses or matricula.quantidade_parcelas or 12))
    bruto_total = float(matricula.valor_total_contrato) if matricula.valor_total_contrato is not None else round(float(matricula.valor_mensalidade or 0.0) * duracao, 2)
    resp.valor_total_contrato = round(bruto_total, 2)

    if matricula.valor_mensalidade is not None:
        desc_pct = float(matricula.desconto_percentual or 0.0)
        desc_fixo = float(getattr(matricula, "desconto_valor_fixo", 0.0) or 0.0)
        liquido_total = max(0.0, bruto_total - round(bruto_total * (desc_pct / 100.0), 2) - desc_fixo)
        qtd_cobr = max(1, int(matricula.quantidade_parcelas or duracao))
        if (matricula.condicao_pagamento or "MENSAL") == CondicaoPagamento.MENSAL.value and desc_fixo == 0.0:
            resp.valor_com_desconto = round(matricula.valor_mensalidade * (1 - desc_pct / 100.0), 2)
        else:
            resp.valor_com_desconto = round(liquido_total / qtd_cobr, 2)

    resp.total_parcelas_geradas = total_parcelas
    return resp


@router.get("/", response_model=List[MatriculaResponse], summary="Listar matrículas")
def list_enrollments(
    aluno_id: Optional[int] = Query(None, description="Filtrar por aluno"),
    turma_id: Optional[int] = Query(None, description="Filtrar por turma"),
    status_filter: Optional[StatusMatricula] = Query(None, alias="status", description="Filtrar por status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Matricula).options(
        joinedload(Matricula.aluno),
        joinedload(Matricula.turma).joinedload(ClassGroup.curso),
        joinedload(Matricula.curso),
    )
    if aluno_id:
        query = query.filter(Matricula.aluno_id == aluno_id)
    if turma_id:
        query = query.filter(Matricula.turma_id == turma_id)
    if status_filter:
        query = query.filter(Matricula.status == status_filter.value)

    matriculas = query.order_by(Matricula.data_matricula.desc()).all()
    contagem_rows = db.query(
        Invoice.matricula_id, func.count(Invoice.id)
    ).filter(
        Invoice.status != StatusTitulo.CANCELADO.value
    ).group_by(Invoice.matricula_id).all()
    contagem_map = {mat_id: total for mat_id, total in contagem_rows}

    return [formatar_matricula_response(m, total_parcelas=contagem_map.get(m.id, 0)) for m in matriculas]


@router.post(
    "/",
    response_model=MatriculaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Realizar matrícula de aluno em turma"
)
def create_enrollment(
    mat_in: MatriculaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    """
    Realiza a matrícula de um aluno aplicando a política de duração do contrato, condição de pagamento,
    planos/descontos (com teto e auditoria de alteração manual) ou modo cortesia sem cobrança.
    """
    client_ip = request.client.host if request.client else None

    aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(
        Aluno.id == mat_in.aluno_id, Aluno.ativo.is_(True)
    ).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ativo não encontrado.")

    turma = db.query(ClassGroup).options(joinedload(ClassGroup.cursos)).filter(
        ClassGroup.id == mat_in.turma_id, ClassGroup.ativa.is_(True)
    ).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma ativa não encontrada.")

    curso_id_efetivo = mat_in.curso_id
    if curso_id_efetivo is not None:
        cursos_da_turma_ids = {c.id for c in (turma.cursos or [])}
        if turma.curso_id is not None:
            cursos_da_turma_ids.add(turma.curso_id)
        if cursos_da_turma_ids and curso_id_efetivo not in cursos_da_turma_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O curso selecionado não está associado à turma escolhida."
            )
    elif turma.cursos and len(turma.cursos) == 1:
        curso_id_efetivo = turma.cursos[0].id
    elif turma.curso_id is not None:
        curso_id_efetivo = turma.curso_id

    matricula_existente = db.query(Matricula).filter(
        Matricula.aluno_id == mat_in.aluno_id,
        Matricula.turma_id == mat_in.turma_id,
        Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value])
    ).first()
    if matricula_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este aluno já possui matrícula ativa nesta turma."
        )

    vagas_ocupadas = contar_matriculas_ativas(db, mat_in.turma_id)
    if vagas_ocupadas >= turma.capacidade_maxima:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A turma '{turma.nome}' está com capacidade máxima atingida "
                f"({vagas_ocupadas}/{turma.capacidade_maxima} alunos). "
                "Use a lista de espera para registrar o interesse do aluno."
            )
        )

    duracao_meses = max(1, int(mat_in.duracao_contrato_meses or mat_in.quantidade_parcelas or 12))
    condicao = mat_in.condicao_pagamento.value
    if condicao == CondicaoPagamento.A_VISTA.value:
        qtd_parcelas = 1
    elif condicao == CondicaoPagamento.PARCELADO.value:
        qtd_parcelas = min(12, max(1, int(mat_in.quantidade_parcelas or 1)))
    else:
        qtd_parcelas = duracao_meses

    sim = simular_politica_desconto(
        db=db,
        curso_id=curso_id_efetivo,
        valor_mensalidade=mat_in.valor_mensalidade,
        duracao_contrato_meses=duracao_meses,
        condicao_pagamento=condicao,
        quantidade_parcelas=qtd_parcelas,
        plano_id=mat_in.plano_id,
        descontos_ids=mat_in.descontos_ids or [],
        desconto_valor_fixo=mat_in.desconto_valor_fixo or 0.0,
    )

    pct_politica = sim["percentual_aplicado"]
    pct_final = float(mat_in.desconto_percentual) if mat_in.desconto_percentual is not None else pct_politica
    fixo_final = round(float(mat_in.desconto_valor_fixo or 0.0), 2)

    editado_manual = bool(mat_in.desconto_editado_manualmente) or (
        mat_in.desconto_percentual is not None and abs(pct_final - pct_politica) > 0.001
    )
    if fixo_final > 0 and mat_in.desconto_editado_manualmente is not False:
        editado_manual = True

    numero_contrato = f"MAT-{date.today().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"
    status_inicial = StatusMatricula.EXPERIMENTAL.value if mat_in.aula_experimental else StatusMatricula.ATIVA.value
    dia_vencimento = mat_in.dia_vencimento or 10

    tipo_desc = mat_in.tipo_desconto
    if not tipo_desc and sim["itens_aplicados"]:
        if len(sim["itens_aplicados"]) > 1:
            tipo_desc = "combinado"
        elif sim["itens_aplicados"][0].get("tipo") == "PLANO":
            tipo_desc = "plano"

    agora = datetime.now(timezone.utc)
    nova_matricula = Matricula(
        aluno_id=mat_in.aluno_id,
        turma_id=mat_in.turma_id,
        curso_id=curso_id_efetivo,
        status=status_inicial,
        data_matricula=mat_in.data_matricula,
        data_inicio=mat_in.data_inicio,
        data_termino_previsto=mat_in.data_termino_previsto,
        data_saida=mat_in.data_saida,
        numero_contrato=numero_contrato,
        contrato_assinado=False,
        valor_mensalidade=mat_in.valor_mensalidade,
        duracao_contrato_meses=duracao_meses,
        valor_total_contrato=sim["valor_total_bruto"],
        condicao_pagamento=condicao,
        plano_id=mat_in.plano_id,
        plano_nome=sim["plano_nome"],
        desconto_percentual=pct_final,
        desconto_valor_fixo=fixo_final,
        desconto_plano_percentual=sim["desconto_plano_percentual"],
        desconto_adicional_percentual=sim["desconto_adicional_percentual"],
        descontos_aplicados_json=json.dumps(sim["itens_aplicados"], ensure_ascii=False) if sim["itens_aplicados"] else None,
        tipo_desconto=tipo_desc,
        desconto_editado_manualmente=editado_manual,
        desconto_alterado_por_id=current_user.id if editado_manual else None,
        desconto_alterado_por_nome=current_user.nome if editado_manual else None,
        desconto_motivo_alteracao=mat_in.desconto_motivo_alteracao if editado_manual else None,
        desconto_alterado_em=agora if editado_manual else None,
        dia_vencimento=dia_vencimento,
        quantidade_parcelas=qtd_parcelas,
        aula_experimental=mat_in.aula_experimental,
        is_cortesia=mat_in.is_cortesia,
        tipo_cortesia=mat_in.tipo_cortesia.value if mat_in.tipo_cortesia else None,
        observacoes=mat_in.observacoes
    )
    db.add(nova_matricula)
    db.flush()

    faturas_geradas = gerar_faturas_matricula(db, nova_matricula, aluno=aluno, turma=turma)

    db.commit()
    db.refresh(nova_matricula)

    registrar_auditoria(
        db=db,
        acao="MATRICULA_CRIADA",
        entidade="Matricula",
        registro_id=str(nova_matricula.id),
        detalhes={
            "aluno": aluno.nome,
            "turma": turma.nome,
            "contrato": numero_contrato,
            "duracao_meses": duracao_meses,
            "condicao_pagamento": condicao,
            "experimental": mat_in.aula_experimental,
            "cortesia": mat_in.is_cortesia,
            "tipo_cortesia": nova_matricula.tipo_cortesia,
            "desconto_percentual": pct_final,
            "desconto_valor_fixo": fixo_final,
            "desconto_manual": editado_manual,
            "parcelas_geradas": len(faturas_geradas)
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(nova_matricula, total_parcelas=len(faturas_geradas))


@router.get("/{matricula_id}", response_model=MatriculaResponse, summary="Obter dados da matrícula")
def get_enrollment(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno),
        joinedload(Matricula.turma).joinedload(ClassGroup.curso),
        joinedload(Matricula.curso),
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")
    return formatar_matricula_response(matricula, total_parcelas=contar_parcelas_matricula(db, matricula.id))


@router.put("/{matricula_id}", response_model=MatriculaResponse, summary="Atualizar matrícula (status, contrato, datas, descontos)")
def update_enrollment(
    matricula_id: int,
    mat_update: MatriculaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.FINANCEIRO.value
    ))
):
    client_ip = request.client.host if request.client else None
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma).joinedload(ClassGroup.cursos),
        joinedload(Matricula.curso),
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    if mat_update.status is not None:
        if mat_update.status == StatusMatricula.CANCELADA:
            if not mat_update.motivo_cancelamento:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Para cancelamento de matrícula é obrigatório informar o motivo."
                )
            matricula.motivo_cancelamento = mat_update.motivo_cancelamento
            matricula.data_cancelamento = datetime.now(timezone.utc)
            matricula.multa_cancelamento = mat_update.multa_cancelamento or 0.0
            if mat_update.data_saida is None and matricula.data_saida is None:
                matricula.data_saida = date.today()
        matricula.status = mat_update.status.value
        if mat_update.status == StatusMatricula.ATIVA and mat_update.aula_experimental is None:
            matricula.aula_experimental = False
        elif mat_update.status == StatusMatricula.EXPERIMENTAL and mat_update.aula_experimental is None:
            matricula.aula_experimental = True

    if mat_update.data_termino_previsto is not None:
        matricula.data_termino_previsto = mat_update.data_termino_previsto
    if mat_update.data_saida is not None:
        matricula.data_saida = mat_update.data_saida

    if mat_update.aula_experimental is not None:
        matricula.aula_experimental = mat_update.aula_experimental
    if mat_update.is_cortesia is not None:
        matricula.is_cortesia = mat_update.is_cortesia
        if not mat_update.is_cortesia:
            matricula.tipo_cortesia = None
    if mat_update.tipo_cortesia is not None:
        matricula.tipo_cortesia = mat_update.tipo_cortesia.value

    if mat_update.contrato_assinado is not None:
        matricula.contrato_assinado = mat_update.contrato_assinado
        if mat_update.contrato_assinado:
            matricula.data_assinatura_contrato = datetime.now(timezone.utc)

    if mat_update.curso_id is not None:
        turma = matricula.turma
        if turma:
            cursos_ids = {c.id for c in (turma.cursos or [])}
            if turma.curso_id is not None:
                cursos_ids.add(turma.curso_id)
            if cursos_ids and mat_update.curso_id not in cursos_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="O curso selecionado não está associado à turma da matrícula."
                )
        matricula.curso_id = mat_update.curso_id

    if mat_update.valor_mensalidade is not None:
        matricula.valor_mensalidade = mat_update.valor_mensalidade
    if mat_update.duracao_contrato_meses is not None:
        matricula.duracao_contrato_meses = mat_update.duracao_contrato_meses
    if mat_update.condicao_pagamento is not None:
        matricula.condicao_pagamento = mat_update.condicao_pagamento.value
    if mat_update.dia_vencimento is not None:
        matricula.dia_vencimento = mat_update.dia_vencimento
    if mat_update.quantidade_parcelas is not None:
        matricula.quantidade_parcelas = mat_update.quantidade_parcelas
        if mat_update.duracao_contrato_meses is None and matricula.condicao_pagamento == CondicaoPagamento.MENSAL.value:
            matricula.duracao_contrato_meses = mat_update.quantidade_parcelas

    if matricula.condicao_pagamento == CondicaoPagamento.A_VISTA.value:
        matricula.quantidade_parcelas = 1
    elif matricula.condicao_pagamento == CondicaoPagamento.MENSAL.value:
        matricula.quantidade_parcelas = matricula.duracao_contrato_meses
    matricula.valor_total_contrato = round(
        float(matricula.valor_mensalidade or 0.0) * max(1, int(matricula.duracao_contrato_meses or 12)),
        2
    )

    desconto_alterado = False
    if mat_update.desconto_percentual is not None and abs(mat_update.desconto_percentual - float(matricula.desconto_percentual or 0.0)) > 0.001:
        matricula.desconto_percentual = mat_update.desconto_percentual
        desconto_alterado = True
    if mat_update.desconto_valor_fixo is not None and abs(mat_update.desconto_valor_fixo - float(matricula.desconto_valor_fixo or 0.0)) > 0.001:
        matricula.desconto_valor_fixo = mat_update.desconto_valor_fixo
        desconto_alterado = True

    if desconto_alterado or mat_update.desconto_editado_manualmente:
        matricula.desconto_editado_manualmente = True
        matricula.desconto_alterado_por_id = current_user.id
        matricula.desconto_alterado_por_nome = current_user.nome
        matricula.desconto_alterado_em = datetime.now(timezone.utc)
        if mat_update.desconto_motivo_alteracao is not None:
            matricula.desconto_motivo_alteracao = mat_update.desconto_motivo_alteracao
    elif mat_update.desconto_motivo_alteracao is not None:
        matricula.desconto_motivo_alteracao = mat_update.desconto_motivo_alteracao

    if mat_update.tipo_desconto is not None:
        matricula.tipo_desconto = mat_update.tipo_desconto
    if mat_update.observacoes is not None:
        matricula.observacoes = mat_update.observacoes

    sync_result = sincronizar_faturas_matricula(
        db, matricula, aluno=matricula.aluno, turma=matricula.turma
    )

    db.commit()
    db.refresh(matricula)
    total_parcelas = contar_parcelas_matricula(db, matricula.id)

    registrar_auditoria(
        db=db,
        acao="MATRICULA_ATUALIZADA",
        entidade="Matricula",
        registro_id=str(matricula.id),
        detalhes={
            "status": matricula.status,
            "contrato_assinado": matricula.contrato_assinado,
            "data_saida": str(matricula.data_saida) if matricula.data_saida else None,
            "parcelas_geradas": len(sync_result["geradas"]),
            "parcelas_atualizadas": sync_result["atualizadas"],
            "parcelas_canceladas": sync_result["canceladas"]
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(matricula, total_parcelas=total_parcelas)


@router.delete(
    "/{matricula_id}",
    status_code=status.HTTP_200_OK,
    summary="Excluir matrícula (quando não houver faturas pagas)"
)
def delete_enrollment(
    matricula_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.FINANCEIRO.value
    ))
):
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno),
        joinedload(Matricula.turma)
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    faturas_pagas = db.query(Invoice).filter(
        Invoice.matricula_id == matricula_id,
        Invoice.status == StatusTitulo.PAGO.value
    ).count()
    if faturas_pagas > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esta matrícula possui mensalidade(s) já paga(s) e não pode ser excluída. "
                "Use a opção de editar matrícula para cancelar ou trancar preservando o histórico financeiro."
            )
        )

    aluno_nome = matricula.aluno.nome if matricula.aluno else f"Aluno #{matricula.aluno_id}"
    turma_nome = matricula.turma.nome if matricula.turma else f"Turma #{matricula.turma_id}"

    db.query(Invoice).filter(Invoice.matricula_id == matricula_id).delete(synchronize_session=False)
    db.delete(matricula)
    db.commit()

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="MATRICULA_EXCLUIDA",
        entidade="Matricula",
        registro_id=str(matricula_id),
        detalhes={"aluno": aluno_nome, "turma": turma_nome},
        usuario=current_user,
        ip=client_ip
    )
    return {
        "status": "ok",
        "mensagem": f"Matrícula de '{aluno_nome}' na turma '{turma_nome}' excluída com sucesso."
    }


@router.post(
    "/{matricula_id}/generate-invoices",
    summary="Gerar parcelas faltantes de uma matrícula ativa"
)
def generate_enrollment_invoices(
    matricula_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.FINANCEIRO.value
    ))
):
    client_ip = request.client.host if request.client else None
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma),
        joinedload(Matricula.curso),
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    if matricula.status in [StatusMatricula.CANCELADA.value, StatusMatricula.TRANCADA.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula cancelada ou trancada não pode gerar novas faturas."
        )

    if matricula.status == StatusMatricula.EXPERIMENTAL.value or matricula.aula_experimental:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula experimental não gera cobrança financeira. Edite o status para ATIVA antes de gerar parcelas."
        )

    if getattr(matricula, "is_cortesia", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula cortesia / sem cobrança não gera faturas no Financeiro."
        )

    novas = gerar_faturas_matricula(db, matricula, aluno=matricula.aluno, turma=matricula.turma)
    db.commit()
    total_parcelas = contar_parcelas_matricula(db, matricula.id)

    if novas:
        registrar_auditoria(
            db=db,
            acao="PARCELAS_MATRICULA_GERADAS",
            entidade="Matricula",
            registro_id=str(matricula.id),
            detalhes={"parcelas_geradas": len(novas), "total_parcelas": total_parcelas},
            usuario=current_user,
            ip=client_ip
        )

    return {
        "matricula_id": matricula.id,
        "parcelas_geradas": len(novas),
        "total_parcelas": total_parcelas,
        "mensagem": (
            f"{len(novas)} parcela(s) gerada(s) com sucesso!"
            if novas else
            "Todas as parcelas desta matrícula já estão geradas no Financeiro."
        )
    }


# ─── Lista de Espera ──────────────────────────────────────────────────────────

@router.post(
    "/waitlist",
    response_model=ListaEsperaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar aluno à lista de espera de uma turma"
)
def add_to_waitlist(
    espera_in: ListaEsperaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    aluno = db.query(Aluno).filter(Aluno.id == espera_in.aluno_id, Aluno.ativo.is_(True)).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ativo não encontrado.")

    turma = db.query(ClassGroup).filter(ClassGroup.id == espera_in.turma_id, ClassGroup.ativa.is_(True)).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma ativa não encontrada.")

    ja_na_fila = db.query(ListaEspera).filter(
        ListaEspera.aluno_id == espera_in.aluno_id,
        ListaEspera.turma_id == espera_in.turma_id,
        ListaEspera.ativa.is_(True)
    ).first()
    if ja_na_fila:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Aluno já está na lista de espera da turma '{turma.nome}' (posição {ja_na_fila.posicao})."
        )

    ultima_posicao = db.query(ListaEspera).filter(
        ListaEspera.turma_id == espera_in.turma_id,
        ListaEspera.ativa.is_(True)
    ).count()

    nova_entrada = ListaEspera(
        aluno_id=espera_in.aluno_id,
        turma_id=espera_in.turma_id,
        posicao=ultima_posicao + 1,
        ativa=True,
        notificado=False,
        observacoes=espera_in.observacoes
    )
    db.add(nova_entrada)
    db.commit()
    db.refresh(nova_entrada)

    resp = ListaEsperaResponse.model_validate(nova_entrada)
    resp.aluno_nome = aluno.nome
    resp.turma_nome = turma.nome
    return resp


@router.get(
    "/waitlist/{turma_id}",
    response_model=List[ListaEsperaResponse],
    summary="Listar fila de espera de uma turma"
)
def get_waitlist(
    turma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    entradas = db.query(ListaEspera).options(
        joinedload(ListaEspera.aluno), joinedload(ListaEspera.turma)
    ).filter(
        ListaEspera.turma_id == turma_id,
        ListaEspera.ativa.is_(True)
    ).order_by(ListaEspera.posicao.asc()).all()

    result = []
    for e in entradas:
        resp = ListaEsperaResponse.model_validate(e)
        if e.aluno:
            resp.aluno_nome = e.aluno.nome
        if e.turma:
            resp.turma_nome = e.turma.nome
        result.append(resp)
    return result
