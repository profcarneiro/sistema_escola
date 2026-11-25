import calendar
import json
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.attendance import Attendance, ClassMakeUp, Lesson, StatusPresenca, StatusReposicao
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Expense, FormaPagamento, Invoice, SituacaoDespesa, StatusTitulo
from app.models.operations import (
    AttendanceChangeLog,
    CommercialConfig,
    CommercialPayout,
    ModalidadePagamentoProfessor,
    ModoPagamentoPercentual,
    StatusFechamento,
    TeacherClosing,
    TeacherPaymentRule,
    WorkshopParticipant,
    WorkshopSession,
)
from app.models.student import Aluno
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.routers.auth import get_current_active_user, require_roles
from app.schemas.operations import (
    CommercialClosingPayRequest,
    CommercialConfigResponse,
    CommercialConfigUpdate,
    CommercialPayoutResponse,
    TeacherClosingGenerateRequest,
    TeacherClosingPayRequest,
    TeacherClosingResponse,
    TeacherPaymentRuleResponse,
    TeacherPaymentRuleUpsert,
    WorkshopMonthlySummaryResponse,
    WorkshopParticipantCreate,
    WorkshopParticipantResponse,
    WorkshopPayTransferRequest,
    WorkshopSessionCreate,
    WorkshopSessionResponse,
)
from app.services.cost_centers import get_general_cost_center_id, get_or_create_course_cost_center

router = APIRouter(prefix="/operations", tags=["Operacional (Professores, Comercial e Ateliê)"])


def _month_bounds(competencia: str) -> tuple[date, date]:
    ano, mes = map(int, competencia.split("-"))
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return inicio, fim


def _format_rule(rule: TeacherPaymentRule) -> TeacherPaymentRuleResponse:
    resp = TeacherPaymentRuleResponse.model_validate(rule)
    resp.professor_nome = rule.professor.nome if rule.professor else None
    resp.curso_nome = rule.curso.nome if rule.curso else "Padrão (todos os cursos)"
    return resp


def _format_closing(closing: TeacherClosing) -> TeacherClosingResponse:
    detalhes = []
    if closing.detalhes_json:
        try:
            detalhes = json.loads(closing.detalhes_json)
        except Exception:
            detalhes = []
    return TeacherClosingResponse(
        id=closing.id,
        professor_id=closing.professor_id,
        professor_nome=closing.professor.nome if closing.professor else None,
        competencia=closing.competencia,
        total_aulas_dadas=closing.total_aulas_dadas,
        total_presencas=closing.total_presencas,
        valor_por_presenca_total=closing.valor_por_presenca_total,
        valor_percentual_total=closing.valor_percentual_total,
        valor_fixo_total=closing.valor_fixo_total,
        valor_total=closing.valor_total,
        valor_pago=closing.valor_pago,
        saldo_a_pagar=closing.saldo_a_pagar,
        status=StatusFechamento(closing.status),
        data_pagamento=closing.data_pagamento,
        forma_pagamento=closing.forma_pagamento,
        conciliado_extrato=closing.conciliado_extrato,
        referencia_extrato=closing.referencia_extrato,
        detalhes=detalhes,
        expense_id=closing.expense_id,
        observacoes=closing.observacoes,
        atualizado_em=closing.atualizado_em,
    )


def _format_workshop(ws: WorkshopSession) -> WorkshopSessionResponse:
    part_resps = [WorkshopParticipantResponse.model_validate(p) for p in (ws.participantes or [])]
    receita_bruta = round(sum(float(p.valor_pago or 0.0) for p in part_resps), 2)
    parte_escola = round(receita_bruta * (float(ws.percentual_escola or 0.0) / 100.0), 2)
    valor_repasse = round(receita_bruta * (float(ws.percentual_professora or 0.0) / 100.0), 2)
    resultado_escola = round(parte_escola - float(ws.despesas_materiais or 0.0), 2)
    return WorkshopSessionResponse(
        id=ws.id,
        titulo=ws.titulo,
        modalidade=ws.modalidade,
        professora_parceira=ws.professora_parceira,
        data_realizacao=ws.data_realizacao,
        competencia=ws.competencia,
        curso_id=ws.curso_id,
        centro_custo_id=ws.centro_custo_id,
        percentual_escola=ws.percentual_escola,
        percentual_professora=ws.percentual_professora,
        despesas_materiais=ws.despesas_materiais,
        repasse_pago=ws.repasse_pago,
        data_repasse=ws.data_repasse,
        forma_repasse=ws.forma_repasse,
        observacoes=ws.observacoes,
        receita_bruta=receita_bruta,
        parte_escola=parte_escola,
        valor_repassar_professora=valor_repasse,
        resultado_escola=resultado_escola,
        participantes=part_resps,
    )


# ─── Pagamento de Professores: Regras ─────────────────────────────────────────

@router.get(
    "/teachers/rules",
    response_model=List[TeacherPaymentRuleResponse],
    summary="Listar regras de remuneração por professor e curso"
)
def list_teacher_rules(
    professor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    query = db.query(TeacherPaymentRule).options(
        joinedload(TeacherPaymentRule.professor),
        joinedload(TeacherPaymentRule.curso),
    )
    if professor_id is not None:
        query = query.filter(TeacherPaymentRule.professor_id == professor_id)
    rules = query.order_by(TeacherPaymentRule.professor_id.asc(), TeacherPaymentRule.curso_id.asc()).all()
    return [_format_rule(r) for r in rules]


@router.put(
    "/teachers/rules",
    response_model=TeacherPaymentRuleResponse,
    summary="Criar ou atualizar regra de remuneração de professor por curso"
)
def upsert_teacher_rule(
    rule_in: TeacherPaymentRuleUpsert,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    prof = db.query(Teacher).filter(Teacher.id == rule_in.professor_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")
    if rule_in.curso_id is not None:
        curso = db.query(Course).filter(Course.id == rule_in.curso_id).first()
        if not curso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado.")

    query = db.query(TeacherPaymentRule).filter(TeacherPaymentRule.professor_id == rule_in.professor_id)
    if rule_in.curso_id is None:
        existing = query.filter(TeacherPaymentRule.curso_id.is_(None)).first()
    else:
        existing = query.filter(TeacherPaymentRule.curso_id == rule_in.curso_id).first()

    if existing:
        existing.modalidade = rule_in.modalidade.value
        existing.valor_por_presenca = round(float(rule_in.valor_por_presenca), 2)
        existing.percentual_curso = round(float(rule_in.percentual_curso), 2)
        existing.pagamento_percentual_modo = rule_in.pagamento_percentual_modo.value
        existing.valor_fixo_mensal = round(float(rule_in.valor_fixo_mensal), 2)
        existing.pagar_experimental = bool(rule_in.pagar_experimental)
        existing.pagar_cortesia = bool(rule_in.pagar_cortesia)
        existing.ativo = bool(rule_in.ativo)
        alvo = existing
    else:
        alvo = TeacherPaymentRule(
            professor_id=rule_in.professor_id,
            curso_id=rule_in.curso_id,
            modalidade=rule_in.modalidade.value,
            valor_por_presenca=round(float(rule_in.valor_por_presenca), 2),
            percentual_curso=round(float(rule_in.percentual_curso), 2),
            pagamento_percentual_modo=rule_in.pagamento_percentual_modo.value,
            valor_fixo_mensal=round(float(rule_in.valor_fixo_mensal), 2),
            pagar_experimental=bool(rule_in.pagar_experimental),
            pagar_cortesia=bool(rule_in.pagar_cortesia),
            ativo=bool(rule_in.ativo),
        )
        db.add(alvo)

    db.commit()
    alvo = db.query(TeacherPaymentRule).options(
        joinedload(TeacherPaymentRule.professor),
        joinedload(TeacherPaymentRule.curso),
    ).filter(TeacherPaymentRule.id == alvo.id).first()

    registrar_auditoria(
        db=db,
        acao="REGRA_PROFESSOR_SALVA",
        entidade="TeacherPaymentRule",
        registro_id=str(alvo.id),
        detalhes={"professor_id": alvo.professor_id, "curso_id": alvo.curso_id, "modalidade": alvo.modalidade},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return _format_rule(alvo)


@router.delete("/teachers/rules/{rule_id}", summary="Excluir regra de pagamento de professor")
def delete_teacher_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    rule = db.query(TeacherPaymentRule).filter(TeacherPaymentRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada.")
    db.delete(rule)
    db.commit()
    return {"mensagem": "Regra removida com sucesso."}


# ─── Pagamento de Professores: Fechamento Mensal ─────────────────────────────

def _sync_teacher_closing_expenses(
    db: Session,
    closing: TeacherClosing,
    professor: Teacher,
    competencia: str,
    totais_por_curso: Dict[Optional[int], float],
) -> Optional[int]:
    """Cria/atualiza despesas operacionais no(s) centro(s) de custo dos cursos para o fechamento."""
    inicio_mes, fim_mes = _month_bounds(competencia)
    despesas_antigas = db.query(Expense).filter(
        Expense.origem_tipo == "TEACHER_CLOSING",
        Expense.origem_id == closing.id,
    ).all()
    for d in despesas_antigas:
        db.delete(d)
    db.flush()

    first_expense_id = None
    is_pago_total = closing.status == StatusFechamento.PAGO.value
    ratio_pago = (closing.valor_pago / closing.valor_total) if closing.valor_total > 0 else 0.0

    for cid, subtotal in totais_por_curso.items():
        subtotal = round(float(subtotal), 2)
        if subtotal <= 0:
            continue
        if cid:
            curso = db.query(Course).filter(Course.id == cid).first()
            cc_id = get_or_create_course_cost_center(db, curso).id if curso else get_general_cost_center_id(db, "ESTRUTURA")
            curso_label = curso.nome if curso else f"Curso #{cid}"
        else:
            cc_id = get_general_cost_center_id(db, "ESTRUTURA")
            curso_label = "Geral"

        v_pago = subtotal if is_pago_total else (round(subtotal * ratio_pago, 2) if closing.valor_pago > 0 else 0.0)
        exp = Expense(
            categoria="Pagamento Professor",
            descricao=f"Professor {professor.nome} - {curso_label} ({competencia})",
            valor=v_pago if (is_pago_total and v_pago > 0) else subtotal,
            valor_previsto=subtotal,
            valor_pago=v_pago,
            data_competencia=inicio_mes,
            data_vencimento=fim_mes,
            data_pagamento=closing.data_pagamento if is_pago_total else None,
            pago=is_pago_total,
            situacao=SituacaoDespesa.PAGO.value if is_pago_total else SituacaoDespesa.EM_ABERTO.value,
            forma_pagamento=closing.forma_pagamento or FormaPagamento.PIX.value,
            centro_custo_id=cc_id,
            origem_tipo="TEACHER_CLOSING",
            origem_id=closing.id,
        )
        db.add(exp)
        db.flush()
        if first_expense_id is None:
            first_expense_id = exp.id

    closing.expense_id = first_expense_id
    return first_expense_id


def _compute_teacher_closing(db: Session, professor: Teacher, competencia: str) -> TeacherClosing:
    inicio_mes, fim_mes = _month_bounds(competencia)

    existente = db.query(TeacherClosing).filter(
        TeacherClosing.professor_id == professor.id,
        TeacherClosing.competencia == competencia,
    ).first()
    if existente and existente.status in (StatusFechamento.PAGO.value, StatusFechamento.PAGO_PARCIAL.value):
        return existente

    regras = db.query(TeacherPaymentRule).options(joinedload(TeacherPaymentRule.curso)).filter(
        TeacherPaymentRule.professor_id == professor.id,
        TeacherPaymentRule.ativo.is_(True),
    ).all()
    regra_por_curso: Dict[Optional[int], TeacherPaymentRule] = {r.curso_id: r for r in regras}
    regra_padrao = regra_por_curso.get(None)

    aulas = db.query(Lesson).options(
        joinedload(Lesson.turma).joinedload(ClassGroup.cursos),
        joinedload(Lesson.frequencias).joinedload(Attendance.aluno),
        joinedload(Lesson.frequencias).joinedload(Attendance.matricula),
    ).filter(
        Lesson.professor_id == professor.id,
        Lesson.data_aula >= inicio_mes,
        Lesson.data_aula <= fim_mes,
    ).order_by(Lesson.data_aula.asc()).all()

    aulas_validas = [a for a in aulas if not a.cancelada_professor]
    aulas_canceladas = [a for a in aulas if a.cancelada_professor]

    detalhes: List[Dict[str, Any]] = []
    totais_por_curso: Dict[Optional[int], float] = {}
    total_presencas_pagaveis = 0
    valor_presenca_total = 0.0
    valor_percentual_total = 0.0
    valor_fixo_total = 0.0
    recorded_makeup_ids = set()

    courses_cache: Dict[int, Course] = {c.id: c for c in db.query(Course).all()}

    def _course_name(cid: Optional[int]) -> str:
        if cid and cid in courses_cache:
            return courses_cache[cid].nome
        return "Sem curso específico"

    # 1) Aulas canceladas pelo professor (informativo com valor R$ 0,00)
    for aula_canc in aulas_canceladas:
        detalhes.append({
            "tipo": "AULA_CANCELADA_PROFESSOR",
            "data": str(aula_canc.data_aula),
            "turma_id": aula_canc.turma_id,
            "turma_nome": aula_canc.turma.nome if aula_canc.turma else f"Turma #{aula_canc.turma_id}",
            "curso_id": aula_canc.turma.curso_id if aula_canc.turma else None,
            "curso_nome": _course_name(aula_canc.turma.curso_id if aula_canc.turma else None),
            "aluno_nome": "-",
            "status_presenca": "CANCELADA",
            "valor": 0.0,
            "observacao": "Aula cancelada pelo professor (sem pagamento)",
        })

    # 2) Chamadas das aulas válidas (inclui reposições presenciais nessa turma)
    for aula in aulas_validas:
        turma = aula.turma
        fallback_curso_id = turma.curso_id if turma and turma.curso_id else (turma.cursos[0].id if turma and turma.cursos else None)
        for att in (aula.frequencias or []):
            if att.makeup_id:
                recorded_makeup_ids.add(att.makeup_id)
            mat = att.matricula
            raw_cid = (mat.curso_id if mat and mat.curso_id else None) or fallback_curso_id
            cid = raw_cid if (raw_cid in regra_por_curso or fallback_curso_id not in regra_por_curso) else fallback_curso_id
            regra = regra_por_curso.get(cid) or regra_padrao
            aluno_nome = att.aluno.nome if att.aluno else f"Aluno #{att.aluno_id}"

            if att.status != StatusPresenca.PRESENTE.value:
                detalhes.append({
                    "tipo": "POR_PRESENCA",
                    "data": str(aula.data_aula),
                    "turma_id": aula.turma_id,
                    "turma_nome": turma.nome if turma else f"Turma #{aula.turma_id}",
                    "curso_id": cid,
                    "curso_nome": _course_name(cid),
                    "aluno_id": att.aluno_id,
                    "aluno_nome": aluno_nome,
                    "status_presenca": att.status,
                    "eh_reposicao": bool(att.eh_reposicao),
                    "valor": 0.0,
                    "observacao": "Falta justificada sem pagamento" if att.status == StatusPresenca.JUSTIFICADA.value else "Falta sem pagamento",
                })
                continue

            is_exp = bool(mat and (mat.aula_experimental or mat.status == StatusMatricula.EXPERIMENTAL.value))
            is_cort = bool(mat and getattr(mat, "is_cortesia", False))

            if is_exp and not (regra and regra.pagar_experimental):
                detalhes.append({
                    "tipo": "POR_PRESENCA",
                    "data": str(aula.data_aula),
                    "turma_id": aula.turma_id,
                    "turma_nome": turma.nome if turma else f"Turma #{aula.turma_id}",
                    "curso_id": cid,
                    "curso_nome": _course_name(cid),
                    "aluno_id": att.aluno_id,
                    "aluno_nome": aluno_nome,
                    "status_presenca": "EXPERIMENTAL",
                    "eh_reposicao": bool(att.eh_reposicao),
                    "valor": 0.0,
                    "observacao": "Aula experimental (não remunerada pela regra)",
                })
                continue

            if is_cort and not (regra and regra.pagar_cortesia):
                detalhes.append({
                    "tipo": "POR_PRESENCA",
                    "data": str(aula.data_aula),
                    "turma_id": aula.turma_id,
                    "turma_nome": turma.nome if turma else f"Turma #{aula.turma_id}",
                    "curso_id": cid,
                    "curso_nome": _course_name(cid),
                    "aluno_id": att.aluno_id,
                    "aluno_nome": aluno_nome,
                    "status_presenca": "CORTESIA",
                    "eh_reposicao": bool(att.eh_reposicao),
                    "valor": 0.0,
                    "observacao": "Matrícula cortesia (não remunerada pela regra)",
                })
                continue

            total_presencas_pagaveis += 1
            if regra and regra.modalidade == ModalidadePagamentoProfessor.POR_PRESENCA.value:
                val = round(float(regra.valor_por_presenca or 0.0), 2)
                valor_presenca_total += val
                totais_por_curso[cid] = totais_por_curso.get(cid, 0.0) + val
                obs = "Reposição realizada com este professor" if att.eh_reposicao else "Presença regular"
                detalhes.append({
                    "tipo": "POR_PRESENCA",
                    "data": str(aula.data_aula),
                    "turma_id": aula.turma_id,
                    "turma_nome": turma.nome if turma else f"Turma #{aula.turma_id}",
                    "curso_id": cid,
                    "curso_nome": _course_name(cid),
                    "aluno_id": att.aluno_id,
                    "aluno_nome": aluno_nome,
                    "status_presenca": "PRESENTE",
                    "eh_reposicao": bool(att.eh_reposicao),
                    "valor": val,
                    "observacao": obs,
                })

    # 3) Reposições marcadas como REALIZADA em ClassMakeUp para este professor sem vínculo direto na chamada
    makeups_realizadas = db.query(ClassMakeUp).options(
        joinedload(ClassMakeUp.aluno),
        joinedload(ClassMakeUp.turma_destino),
        joinedload(ClassMakeUp.matricula_origem),
    ).join(ClassGroup, ClassMakeUp.turma_destino_id == ClassGroup.id).filter(
        ClassGroup.professor_id == professor.id,
        ClassMakeUp.status == StatusReposicao.REALIZADA.value,
        ClassMakeUp.data_reposicao >= inicio_mes,
        ClassMakeUp.data_reposicao <= fim_mes,
    ).all()

    for mk in makeups_realizadas:
        if mk.id in recorded_makeup_ids:
            continue
        cid = (mk.matricula_origem.curso_id if mk.matricula_origem else None) or (mk.turma_destino.curso_id if mk.turma_destino else None)
        regra = regra_por_curso.get(cid) or regra_padrao
        if regra and regra.modalidade == ModalidadePagamentoProfessor.POR_PRESENCA.value:
            val = round(float(regra.valor_por_presenca or 0.0), 2)
            total_presencas_pagaveis += 1
            valor_presenca_total += val
            totais_por_curso[cid] = totais_por_curso.get(cid, 0.0) + val
            detalhes.append({
                "tipo": "REPOSICAO_REALIZADA",
                "data": str(mk.data_reposicao),
                "turma_id": mk.turma_destino_id,
                "turma_nome": mk.turma_destino.nome if mk.turma_destino else f"Turma #{mk.turma_destino_id}",
                "curso_id": cid,
                "curso_nome": _course_name(cid),
                "aluno_id": mk.aluno_id,
                "aluno_nome": mk.aluno.nome if mk.aluno else f"Aluno #{mk.aluno_id}",
                "status_presenca": "PRESENTE",
                "eh_reposicao": True,
                "valor": val,
                "observacao": "Reposição contabilizada para o professor da turma destino",
            })

    # 4) Regras por PERCENTUAL (ex.: Helena 30% em Pintura/Aquarela/Porcelana, Evandro em Moda)
    regras_percentuais = [
        r for r in regras
        if r.modalidade == ModalidadePagamentoProfessor.PERCENTUAL.value and float(r.percentual_curso or 0.0) > 0
    ]
    if regras_percentuais:
        mats_prof = db.query(Matricula).options(
            joinedload(Matricula.aluno),
            joinedload(Matricula.turma),
        ).join(ClassGroup, Matricula.turma_id == ClassGroup.id).filter(
            ClassGroup.professor_id == professor.id,
            Matricula.status != StatusMatricula.CANCELADA.value,
        ).all()

        for mat in mats_prof:
            cid = mat.curso_id or (mat.turma.curso_id if mat.turma else None)
            regra = regra_por_curso.get(cid) or regra_padrao
            if not regra or regra.modalidade != ModalidadePagamentoProfessor.PERCENTUAL.value or regra.percentual_curso <= 0:
                continue
            is_exp = bool(mat.aula_experimental or mat.status == StatusMatricula.EXPERIMENTAL.value)
            is_cort = bool(getattr(mat, "is_cortesia", False))
            if (is_exp and not regra.pagar_experimental) or (is_cort and not regra.pagar_cortesia):
                continue

            pct = float(regra.percentual_curso)
            if regra.pagamento_percentual_modo == ModoPagamentoPercentual.UNICO.value:
                if mat.data_inicio and mat.data_inicio.strftime("%Y-%m") == competencia:
                    base = float(mat.valor_total_liquido if mat.valor_total_liquido is not None else (mat.valor_total_contrato or 0.0))
                    val = round(base * (pct / 100.0), 2)
                    if val > 0:
                        valor_percentual_total += val
                        totais_por_curso[cid] = totais_por_curso.get(cid, 0.0) + val
                        detalhes.append({
                            "tipo": "PERCENTUAL_UNICO",
                            "data": str(mat.data_inicio),
                            "turma_id": mat.turma_id,
                            "turma_nome": mat.turma.nome if mat.turma else f"Turma #{mat.turma_id}",
                            "curso_id": cid,
                            "curso_nome": _course_name(cid),
                            "aluno_id": mat.aluno_id,
                            "aluno_nome": mat.aluno.nome if mat.aluno else f"Aluno #{mat.aluno_id}",
                            "base_calculo": round(base, 2),
                            "percentual": pct,
                            "valor": val,
                            "observacao": f"{pct:g}% à vista sobre contrato único",
                        })
            else:
                faturas_mes = db.query(Invoice).filter(
                    Invoice.matricula_id == mat.id,
                    Invoice.competencia == competencia,
                    Invoice.status != StatusTitulo.CANCELADO.value,
                ).all()
                for inv in faturas_mes:
                    base = float(inv.valor_final or 0.0)
                    val = round(base * (pct / 100.0), 2)
                    if val > 0:
                        valor_percentual_total += val
                        totais_por_curso[cid] = totais_por_curso.get(cid, 0.0) + val
                        detalhes.append({
                            "tipo": "PERCENTUAL_PARCELADO",
                            "data": str(inv.data_vencimento),
                            "turma_id": mat.turma_id,
                            "turma_nome": mat.turma.nome if mat.turma else f"Turma #{mat.turma_id}",
                            "curso_id": cid,
                            "curso_nome": _course_name(cid),
                            "aluno_id": mat.aluno_id,
                            "aluno_nome": mat.aluno.nome if mat.aluno else f"Aluno #{mat.aluno_id}",
                            "base_calculo": round(base, 2),
                            "percentual": pct,
                            "valor": val,
                            "observacao": f"{pct:g}% s/ parcela ({inv.descricao})",
                        })

    # 5) Regras FIXO_MENSAL
    for regra in regras:
        if regra.modalidade == ModalidadePagamentoProfessor.FIXO_MENSAL.value and float(regra.valor_fixo_mensal or 0.0) > 0:
            val = round(float(regra.valor_fixo_mensal), 2)
            valor_fixo_total += val
            totais_por_curso[regra.curso_id] = totais_por_curso.get(regra.curso_id, 0.0) + val
            detalhes.append({
                "tipo": "FIXO_MENSAL",
                "data": str(inicio_mes),
                "turma_id": None,
                "turma_nome": "Salário / Fixo Mensal",
                "curso_id": regra.curso_id,
                "curso_nome": _course_name(regra.curso_id),
                "aluno_nome": "-",
                "valor": val,
                "observacao": "Valor fixo mensal configurado",
            })

    valor_presenca_total = round(valor_presenca_total, 2)
    valor_percentual_total = round(valor_percentual_total, 2)
    valor_fixo_total = round(valor_fixo_total, 2)
    valor_total = round(valor_presenca_total + valor_percentual_total + valor_fixo_total, 2)

    if existente:
        closing = existente
    else:
        closing = TeacherClosing(professor_id=professor.id, competencia=competencia)
        db.add(closing)

    closing.total_aulas_dadas = len(aulas_validas)
    closing.total_presencas = total_presencas_pagaveis
    closing.valor_por_presenca_total = valor_presenca_total
    closing.valor_percentual_total = valor_percentual_total
    closing.valor_fixo_total = valor_fixo_total
    closing.valor_total = valor_total
    closing.valor_pago = 0.0
    closing.saldo_a_pagar = valor_total
    closing.status = StatusFechamento.FECHADO.value
    closing.detalhes_json = json.dumps(detalhes, ensure_ascii=False)
    db.flush()

    _sync_teacher_closing_expenses(db, closing, professor, competencia, totais_por_curso)
    return closing


@router.post(
    "/teachers/closings/generate",
    response_model=List[TeacherClosingResponse],
    summary="Gerar fechamento mensal de professores (integra chamada e centro de custo)"
)
def generate_teacher_closings(
    req: TeacherClosingGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    if req.professor_id is not None:
        prof = db.query(Teacher).filter(Teacher.id == req.professor_id).first()
        if not prof:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")
        professores = [prof]
    else:
        professores = db.query(Teacher).filter(Teacher.ativo.is_(True)).order_by(Teacher.nome.asc()).all()

    closings = []
    for p in professores:
        closings.append(_compute_teacher_closing(db, p, req.competencia))

    db.commit()
    ids = [c.id for c in closings]
    carregados = db.query(TeacherClosing).options(joinedload(TeacherClosing.professor)).filter(TeacherClosing.id.in_(ids)).all()
    registrar_auditoria(
        db=db,
        acao="FECHAMENTO_PROFESSORES_GERADO",
        entidade="TeacherClosing",
        registro_id=req.competencia,
        detalhes={"competencia": req.competencia, "quantidade": len(carregados)},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return [_format_closing(c) for c in carregados]


@router.get(
    "/teachers/closings",
    response_model=List[TeacherClosingResponse],
    summary="Listar fechamentos mensais de professores"
)
def list_teacher_closings(
    competencia: Optional[str] = Query(None),
    professor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    query = db.query(TeacherClosing).options(joinedload(TeacherClosing.professor))
    if competencia:
        query = query.filter(TeacherClosing.competencia == competencia)
    if professor_id is not None:
        query = query.filter(TeacherClosing.professor_id == professor_id)
    rows = query.order_by(TeacherClosing.competencia.desc(), TeacherClosing.professor_id.asc()).all()
    return [_format_closing(r) for r in rows]


@router.post(
    "/teachers/closings/{closing_id}/pay",
    response_model=TeacherClosingResponse,
    summary="Registrar pagamento e conciliação bancária do fechamento de professor"
)
def pay_teacher_closing(
    closing_id: int,
    pay_in: TeacherClosingPayRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    closing = db.query(TeacherClosing).options(joinedload(TeacherClosing.professor)).filter(TeacherClosing.id == closing_id).first()
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento não encontrado.")

    novo_pago = round(float(closing.valor_pago or 0.0) + float(pay_in.valor_pago), 2)
    closing.valor_pago = novo_pago
    closing.saldo_a_pagar = round(max(0.0, float(closing.valor_total or 0.0) - novo_pago), 2)
    closing.data_pagamento = pay_in.data_pagamento
    closing.forma_pagamento = pay_in.forma_pagamento.value
    closing.conciliado_extrato = bool(pay_in.conciliado_extrato)
    if pay_in.referencia_extrato is not None:
        closing.referencia_extrato = pay_in.referencia_extrato.strip()
    if pay_in.observacoes is not None:
        closing.observacoes = pay_in.observacoes
    closing.status = StatusFechamento.PAGO.value if closing.saldo_a_pagar <= 0.0 else StatusFechamento.PAGO_PARCIAL.value

    despesas = db.query(Expense).filter(
        Expense.origem_tipo == "TEACHER_CLOSING",
        Expense.origem_id == closing.id,
    ).all()
    ratio = (closing.valor_pago / closing.valor_total) if closing.valor_total > 0 else 1.0
    for d in despesas:
        d.forma_pagamento = closing.forma_pagamento
        d.data_pagamento = closing.data_pagamento
        if closing.status == StatusFechamento.PAGO.value:
            d.pago = True
            d.situacao = SituacaoDespesa.PAGO.value
            d.valor_pago = d.valor_previsto if d.valor_previsto is not None else d.valor
            d.valor = d.valor_pago
        else:
            d.pago = True
            d.situacao = SituacaoDespesa.PAGO.value
            d.valor_pago = round(float(d.valor_previsto or d.valor) * min(1.0, ratio), 2)

    db.commit()
    db.refresh(closing)

    registrar_auditoria(
        db=db,
        acao="PAGAMENTO_PROFESSOR_REGISTRADO",
        entidade="TeacherClosing",
        registro_id=str(closing.id),
        detalhes={"valor_pago": closing.valor_pago, "status": closing.status, "conciliado": closing.conciliado_extrato},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return _format_closing(closing)


@router.post(
    "/teachers/closings/{closing_id}/reopen",
    response_model=TeacherClosingResponse,
    summary="Reabrir fechamento mensal do professor para permitir ajustes na chamada"
)
def reopen_teacher_closing(
    closing_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value)),
):
    closing = db.query(TeacherClosing).options(joinedload(TeacherClosing.professor)).filter(TeacherClosing.id == closing_id).first()
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento não encontrado.")
    if closing.status == StatusFechamento.PAGO.value or closing.valor_pago > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fechamento já possui pagamento registrado; edite a chamada como Direção informando motivo."
        )
    closing.status = StatusFechamento.ABERTO.value
    db.commit()
    db.refresh(closing)
    registrar_auditoria(
        db=db,
        acao="FECHAMENTO_PROFESSOR_REABERTO",
        entidade="TeacherClosing",
        registro_id=str(closing.id),
        detalhes={"competencia": closing.competencia},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return _format_closing(closing)


@router.get("/teachers/change-logs", summary="Histórico de alterações de chamada após ou durante fechamento")
def list_attendance_change_logs(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.FINANCEIRO.value)),
):
    query = db.query(AttendanceChangeLog)
    if competencia:
        query = query.filter(AttendanceChangeLog.competencia == competencia)
    logs = query.order_by(AttendanceChangeLog.criado_em.desc()).limit(200).all()
    return [
        {
            "id": lg.id,
            "lesson_id": lg.lesson_id,
            "aluno_id": lg.aluno_id,
            "status_anterior": lg.status_anterior,
            "status_novo": lg.status_novo,
            "alterado_por_nome": lg.alterado_por_nome,
            "motivo": lg.motivo,
            "competencia": lg.competencia,
            "criado_em": lg.criado_em,
        }
        for lg in logs
    ]


# ─── Pagamento do Comercial ───────────────────────────────────────────────────

def _get_or_create_commercial_config(db: Session) -> CommercialConfig:
    cfg = db.query(CommercialConfig).filter(CommercialConfig.id == 1).first()
    if not cfg:
        cfg = CommercialConfig(
            id=1,
            nome_responsavel="Comercial HB",
            valor_fixo_mensal=0.0,
            comissao_por_matricula=0.0,
            percentual_sobre_vendas=0.0,
            ativo=True,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.get("/commercial/config", response_model=CommercialConfigResponse, summary="Obter configuração de remuneração do Comercial")
def get_commercial_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    return _get_or_create_commercial_config(db)


@router.put("/commercial/config", response_model=CommercialConfigResponse, summary="Atualizar configuração de remuneração do Comercial")
def update_commercial_config(
    cfg_in: CommercialConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    cfg = _get_or_create_commercial_config(db)
    cfg.nome_responsavel = cfg_in.nome_responsavel.strip()
    cfg.valor_fixo_mensal = round(float(cfg_in.valor_fixo_mensal), 2)
    cfg.comissao_por_matricula = round(float(cfg_in.comissao_por_matricula), 2)
    cfg.percentual_sobre_vendas = round(float(cfg_in.percentual_sobre_vendas), 2)
    cfg.ativo = bool(cfg_in.ativo)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.post("/commercial/closings/generate", response_model=CommercialPayoutResponse, summary="Gerar fechamento mensal do Comercial")
def generate_commercial_closing(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    cfg = _get_or_create_commercial_config(db)
    inicio_mes, fim_mes = _month_bounds(competencia)

    novas_mats = db.query(Matricula).filter(
        Matricula.data_inicio >= inicio_mes,
        Matricula.data_inicio <= fim_mes,
        Matricula.status != StatusMatricula.CANCELADA.value,
        Matricula.aula_experimental.is_(False),
    ).all()
    novas_mats = [m for m in novas_mats if not getattr(m, "is_cortesia", False)]

    qtd_novas = len(novas_mats)
    total_vendas = 0.0
    for m in novas_mats:
        if getattr(m, "valor_total_liquido", None) is not None:
            total_vendas += float(m.valor_total_liquido)
        else:
            dur = m.duracao_contrato_meses or m.quantidade_parcelas or 12
            bruto = float(m.valor_total_contrato or (float(m.valor_mensalidade or 0.0) * dur))
            desc = round(bruto * (float(m.desconto_percentual or 0.0) / 100.0), 2) + float(getattr(m, "desconto_valor_fixo", 0.0) or 0.0)
            total_vendas += max(0.0, bruto - desc)
    total_vendas = round(total_vendas, 2)

    v_fixo = round(float(cfg.valor_fixo_mensal or 0.0), 2) if cfg.ativo else 0.0
    v_comissao = round(qtd_novas * float(cfg.comissao_por_matricula or 0.0), 2) if cfg.ativo else 0.0
    v_pct = round(total_vendas * (float(cfg.percentual_sobre_vendas or 0.0) / 100.0), 2) if cfg.ativo else 0.0
    total_devido = round(v_fixo + v_comissao + v_pct, 2)

    payout = db.query(CommercialPayout).filter(CommercialPayout.competencia == competencia).first()
    if payout and payout.valor_pago > 0:
        return payout
    if not payout:
        payout = CommercialPayout(competencia=competencia, nome_responsavel=cfg.nome_responsavel)
        db.add(payout)

    payout.nome_responsavel = cfg.nome_responsavel
    payout.qtd_matriculas_novas = qtd_novas
    payout.total_vendas_mes = total_vendas
    payout.valor_fixo = v_fixo
    payout.valor_comissao_matriculas = v_comissao
    payout.valor_percentual_vendas = v_pct
    payout.total_devido = total_devido
    payout.valor_pago = 0.0
    payout.saldo = total_devido
    payout.status = SituacaoDespesa.EM_ABERTO.value
    db.flush()

    cc_id = get_general_cost_center_id(db, "MARKETING_CAPTACAO")
    exp = None
    if payout.expense_id:
        exp = db.query(Expense).filter(Expense.id == payout.expense_id).first()
    if total_devido > 0:
        if not exp:
            exp = Expense(
                categoria="Comissão Comercial",
                descricao=f"Comercial {cfg.nome_responsavel} ({competencia})",
                valor=total_devido,
                valor_previsto=total_devido,
                valor_pago=0.0,
                data_competencia=inicio_mes,
                data_vencimento=fim_mes,
                pago=False,
                situacao=SituacaoDespesa.EM_ABERTO.value,
                forma_pagamento=FormaPagamento.PIX.value,
                centro_custo_id=cc_id,
                origem_tipo="COMMERCIAL_PAYOUT",
                origem_id=payout.id,
            )
            db.add(exp)
            db.flush()
            payout.expense_id = exp.id
        else:
            exp.valor = total_devido
            exp.valor_previsto = total_devido
            exp.centro_custo_id = cc_id

    db.commit()
    db.refresh(payout)
    return payout


@router.get("/commercial/closings", response_model=List[CommercialPayoutResponse], summary="Listar fechamentos do Comercial")
def list_commercial_closings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    return db.query(CommercialPayout).order_by(CommercialPayout.competencia.desc()).all()


@router.post("/commercial/closings/{payout_id}/pay", response_model=CommercialPayoutResponse, summary="Registrar pagamento do Comercial")
def pay_commercial_closing(
    payout_id: int,
    pay_in: CommercialClosingPayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    payout = db.query(CommercialPayout).filter(CommercialPayout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento comercial não encontrado.")

    payout.valor_pago = round(float(payout.valor_pago or 0.0) + float(pay_in.valor_pago), 2)
    payout.saldo = round(max(0.0, float(payout.total_devido or 0.0) - payout.valor_pago), 2)
    payout.data_pagamento = pay_in.data_pagamento
    payout.forma_pagamento = pay_in.forma_pagamento.value
    if pay_in.observacoes is not None:
        payout.observacoes = pay_in.observacoes
    payout.status = SituacaoDespesa.PAGO.value if payout.saldo <= 0 else "PAGO_PARCIAL"

    if payout.expense_id:
        exp = db.query(Expense).filter(Expense.id == payout.expense_id).first()
        if exp:
            exp.pago = True
            exp.situacao = SituacaoDespesa.PAGO.value if payout.saldo <= 0 else SituacaoDespesa.EM_ABERTO.value
            exp.valor_pago = payout.valor_pago
            exp.valor = payout.valor_pago
            exp.data_pagamento = payout.data_pagamento
            exp.forma_pagamento = payout.forma_pagamento

    db.commit()
    db.refresh(payout)
    return payout


# ─── Ateliê - Parceria (Workshops e Alunos Avulsos 50/50) ────────────────────

@router.get("/workshops", response_model=List[WorkshopSessionResponse], summary="Listar sessões e workshops de parceria")
def list_workshops(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    )),
):
    query = db.query(WorkshopSession).options(joinedload(WorkshopSession.participantes))
    if competencia:
        query = query.filter(WorkshopSession.competencia == competencia)
    rows = query.order_by(WorkshopSession.data_realizacao.desc(), WorkshopSession.id.desc()).all()
    return [_format_workshop(w) for w in rows]


@router.post("/workshops", response_model=WorkshopSessionResponse, status_code=status.HTTP_201_CREATED, summary="Criar sessão/workshop do Ateliê - Parceria")
def create_workshop(
    ws_in: WorkshopSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    )),
):
    comp = ws_in.data_realizacao.strftime("%Y-%m")
    cc_id = get_general_cost_center_id(db, "ATELIE_PARCERIA")
    if ws_in.curso_id:
        curso = db.query(Course).filter(Course.id == ws_in.curso_id).first()
        if curso:
            cc_id = get_or_create_course_cost_center(db, curso).id

    ws = WorkshopSession(
        titulo=ws_in.titulo.strip(),
        modalidade=ws_in.modalidade.strip(),
        professora_parceira=ws_in.professora_parceira.strip(),
        data_realizacao=ws_in.data_realizacao,
        competencia=comp,
        curso_id=ws_in.curso_id,
        centro_custo_id=cc_id,
        percentual_escola=round(float(ws_in.percentual_escola), 2),
        percentual_professora=round(float(ws_in.percentual_professora), 2),
        despesas_materiais=round(float(ws_in.despesas_materiais), 2),
        observacoes=ws_in.observacoes,
    )
    db.add(ws)
    db.flush()

    for p in ws_in.participantes:
        db.add(WorkshopParticipant(
            workshop_id=ws.id,
            aluno_id=p.aluno_id,
            aluno_nome=p.aluno_nome.strip(),
            telefone=p.telefone,
            valor_pago=round(float(p.valor_pago), 2),
            forma_pagamento=p.forma_pagamento.value,
            observacoes=p.observacoes,
        ))

    if ws.despesas_materiais > 0:
        db.add(Expense(
            categoria="Material",
            descricao=f"Materiais Ateliê Parceria: {ws.titulo} ({ws.data_realizacao.strftime('%d/%m/%Y')})",
            valor=ws.despesas_materiais,
            valor_previsto=ws.despesas_materiais,
            valor_pago=ws.despesas_materiais,
            data_competencia=ws.data_realizacao,
            data_vencimento=ws.data_realizacao,
            data_pagamento=ws.data_realizacao,
            pago=True,
            situacao=SituacaoDespesa.PAGO.value,
            forma_pagamento=FormaPagamento.PIX.value,
            centro_custo_id=cc_id,
            origem_tipo="WORKSHOP_MATERIAL",
            origem_id=ws.id,
        ))

    db.commit()
    ws = db.query(WorkshopSession).options(joinedload(WorkshopSession.participantes)).filter(WorkshopSession.id == ws.id).first()
    return _format_workshop(ws)


@router.post("/workshops/{workshop_id}/participants", response_model=WorkshopSessionResponse, summary="Adicionar aluno avulso ao workshop")
def add_workshop_participant(
    workshop_id: int,
    part_in: WorkshopParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    )),
):
    ws = db.query(WorkshopSession).filter(WorkshopSession.id == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop não encontrado.")
    db.add(WorkshopParticipant(
        workshop_id=ws.id,
        aluno_id=part_in.aluno_id,
        aluno_nome=part_in.aluno_nome.strip(),
        telefone=part_in.telefone,
        valor_pago=round(float(part_in.valor_pago), 2),
        forma_pagamento=part_in.forma_pagamento.value,
        observacoes=part_in.observacoes,
    ))
    db.commit()
    ws = db.query(WorkshopSession).options(joinedload(WorkshopSession.participantes)).filter(WorkshopSession.id == ws.id).first()
    return _format_workshop(ws)


@router.delete("/workshops/participants/{participant_id}", summary="Remover participante avulso do workshop")
def delete_workshop_participant(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    part = db.query(WorkshopParticipant).filter(WorkshopParticipant.id == participant_id).first()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participante não encontrado.")
    db.delete(part)
    db.commit()
    return {"mensagem": "Participante removido com sucesso."}


@router.post("/workshops/{workshop_id}/pay-transfer", response_model=WorkshopSessionResponse, summary="Registrar repasse de 50% à professora parceira")
def pay_workshop_transfer(
    workshop_id: int,
    pay_in: WorkshopPayTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    ws = db.query(WorkshopSession).options(joinedload(WorkshopSession.participantes)).filter(WorkshopSession.id == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop não encontrado.")
    receita_bruta = round(sum(float(p.valor_pago or 0.0) for p in (ws.participantes or [])), 2)
    valor_repasse = round(receita_bruta * (float(ws.percentual_professora or 0.0) / 100.0), 2)

    ws.repasse_pago = True
    ws.data_repasse = pay_in.data_repasse
    ws.forma_repasse = pay_in.forma_repasse.value

    if valor_repasse > 0:
        exp = None
        if ws.expense_id:
            exp = db.query(Expense).filter(Expense.id == ws.expense_id).first()
        if not exp:
            exp = Expense(
                categoria="Repasse Parceria",
                descricao=f"Repasse {ws.percentual_professora:g}% - {ws.professora_parceira} ({ws.titulo})",
                valor=valor_repasse,
                valor_previsto=valor_repasse,
                valor_pago=valor_repasse,
                data_competencia=ws.data_realizacao,
                data_vencimento=pay_in.data_repasse,
                data_pagamento=pay_in.data_repasse,
                pago=True,
                situacao=SituacaoDespesa.PAGO.value,
                forma_pagamento=pay_in.forma_repasse.value,
                centro_custo_id=ws.centro_custo_id or get_general_cost_center_id(db, "ATELIE_PARCERIA"),
                origem_tipo="WORKSHOP_REPASSE",
                origem_id=ws.id,
            )
            db.add(exp)
            db.flush()
            ws.expense_id = exp.id
        else:
            exp.valor = valor_repasse
            exp.valor_previsto = valor_repasse
            exp.valor_pago = valor_repasse
            exp.pago = True
            exp.situacao = SituacaoDespesa.PAGO.value
            exp.data_pagamento = pay_in.data_repasse
            exp.forma_pagamento = pay_in.forma_repasse.value

    db.commit()
    db.refresh(ws)
    return _format_workshop(ws)


@router.delete("/workshops/{workshop_id}", summary="Excluir sessão de workshop do Ateliê - Parceria")
def delete_workshop(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value)),
):
    ws = db.query(WorkshopSession).filter(WorkshopSession.id == workshop_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop não encontrado.")
    desps = db.query(Expense).filter(
        Expense.origem_tipo.in_(["WORKSHOP_MATERIAL", "WORKSHOP_REPASSE"]),
        Expense.origem_id == ws.id,
    ).all()
    for d in desps:
        db.delete(d)
    db.delete(ws)
    db.commit()
    return {"mensagem": "Sessão de workshop removida com sucesso."}


@router.get("/workshops/summary", response_model=WorkshopMonthlySummaryResponse, summary="Resumo mensal do Ateliê - Parceria")
def get_workshops_monthly_summary(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.COORDENACAO.value
    )),
):
    sessions = db.query(WorkshopSession).options(joinedload(WorkshopSession.participantes)).filter(
        WorkshopSession.competencia == competencia
    ).all()

    total_part = 0
    rec_total = 0.0
    mat_total = 0.0
    escola_total = 0.0
    repassar_total = 0.0
    ja_repassado = 0.0

    for ws in sessions:
        total_part += len(ws.participantes or [])
        rec = round(sum(float(p.valor_pago or 0.0) for p in (ws.participantes or [])), 2)
        parte_e = round(rec * (float(ws.percentual_escola or 0.0) / 100.0), 2)
        rep = round(rec * (float(ws.percentual_professora or 0.0) / 100.0), 2)
        rec_total += rec
        mat_total += float(ws.despesas_materiais or 0.0)
        escola_total += parte_e
        repassar_total += rep
        if ws.repasse_pago:
            ja_repassado += rep

    return WorkshopMonthlySummaryResponse(
        competencia=competencia,
        total_sessoes=len(sessions),
        total_participantes=total_part,
        receita_total=round(rec_total, 2),
        despesas_materiais_total=round(mat_total, 2),
        parte_escola_total=round(escola_total, 2),
        valor_repassar_total=round(repassar_total, 2),
        valor_ja_repassado=round(ja_repassado, 2),
        saldo_a_repassar=round(max(0.0, repassar_total - ja_repassado), 2),
        resultado_liquido_escola=round(escola_total - mat_total, 2),
    )
