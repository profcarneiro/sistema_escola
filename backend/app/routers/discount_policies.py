import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.discount_policy import PaymentPlan, CourseDiscountRule, DiscountSettings
from app.models.course import Course
from app.models.enrollment import Matricula
from app.models.user import User, UserRole
from app.routers.auth import get_current_active_user, require_roles
from app.schemas.discount_policy import (
    PaymentPlanCreate,
    PaymentPlanUpdate,
    PaymentPlanResponse,
    CourseDiscountRuleUpsert,
    CourseDiscountRuleResponse,
    DiscountSettingsUpdate,
    DiscountSettingsResponse,
    DiscountPolicyBundleResponse,
    DiscountSimulateRequest,
    DiscountSimulateResponse,
)
from app.services.discount_policy import ensure_default_discount_policies, simular_politica_desconto

router = APIRouter(prefix="/discount-policies", tags=["Planos e Descontos"])


def _slug_codigo(nome: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", nome.strip().upper()).strip("_")
    return (base or "PLANO")[:45]


def _format_rule(rule: CourseDiscountRule) -> CourseDiscountRuleResponse:
    resp = CourseDiscountRuleResponse.model_validate(rule)
    if rule.curso:
        resp.curso_nome = rule.curso.nome
    if rule.plano:
        resp.plano_nome = rule.plano.nome
    return resp


@router.get("/", response_model=DiscountPolicyBundleResponse, summary="Listar planos, descontos, teto e regras por curso")
def get_discount_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    settings_row = ensure_default_discount_policies(db)
    planos = db.query(PaymentPlan).order_by(PaymentPlan.tipo.desc(), PaymentPlan.id.asc()).all()
    regras = db.query(CourseDiscountRule).options(
        joinedload(CourseDiscountRule.curso),
        joinedload(CourseDiscountRule.plano),
    ).all()
    return DiscountPolicyBundleResponse(
        configuracoes=DiscountSettingsResponse.model_validate(settings_row),
        planos=[PaymentPlanResponse.model_validate(p) for p in planos],
        regras_cursos=[_format_rule(r) for r in regras],
    )


@router.put("/settings", response_model=DiscountSettingsResponse, summary="Atualizar teto máximo de descontos")
def update_discount_settings(
    payload: DiscountSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value)),
):
    settings_row = ensure_default_discount_policies(db)
    settings_row.teto_maximo_desconto_percentual = payload.teto_maximo_desconto_percentual
    settings_row.atualizado_por_id = current_user.id
    db.commit()
    db.refresh(settings_row)

    registrar_auditoria(
        db=db,
        acao="TETO_DESCONTO_ATUALIZADO",
        entidade="DiscountSettings",
        registro_id="1",
        detalhes={"teto_maximo_desconto_percentual": settings_row.teto_maximo_desconto_percentual},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return settings_row


@router.post("/plans", response_model=PaymentPlanResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo plano ou tipo de desconto")
def create_payment_plan(
    plan_in: PaymentPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value)),
):
    ensure_default_discount_policies(db)
    codigo = (plan_in.codigo.strip().upper() if plan_in.codigo else _slug_codigo(plan_in.nome))
    if db.query(PaymentPlan).filter(PaymentPlan.codigo == codigo).first():
        sufixo = db.query(PaymentPlan).count() + 1
        codigo = f"{codigo[:40]}_{sufixo}"

    novo = PaymentPlan(
        codigo=codigo,
        nome=plan_in.nome.strip(),
        tipo=plan_in.tipo.value,
        condicao_pagamento=plan_in.condicao_pagamento.value if plan_in.condicao_pagamento else None,
        percentual_desconto=plan_in.percentual_desconto,
        meses_minimos=plan_in.meses_minimos,
        descricao=plan_in.descricao.strip() if plan_in.descricao else None,
        padrao=False,
        ativo=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    registrar_auditoria(
        db=db,
        acao="PLANO_DESCONTO_CRIADO",
        entidade="PaymentPlan",
        registro_id=str(novo.id),
        detalhes={"codigo": novo.codigo, "nome": novo.nome, "percentual": novo.percentual_desconto},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return novo


@router.put("/plans/{plan_id}", response_model=PaymentPlanResponse, summary="Editar plano ou percentual de desconto")
def update_payment_plan(
    plan_id: int,
    plan_up: PaymentPlanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value)),
):
    plano = db.query(PaymentPlan).filter(PaymentPlan.id == plan_id).first()
    if not plano:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano ou desconto não encontrado.")

    if plan_up.nome is not None:
        plano.nome = plan_up.nome.strip()
    if plan_up.tipo is not None:
        plano.tipo = plan_up.tipo.value
    if "condicao_pagamento" in plan_up.model_fields_set:
        plano.condicao_pagamento = plan_up.condicao_pagamento.value if plan_up.condicao_pagamento else None
    if plan_up.percentual_desconto is not None:
        plano.percentual_desconto = plan_up.percentual_desconto
    if "meses_minimos" in plan_up.model_fields_set:
        plano.meses_minimos = plan_up.meses_minimos
    if plan_up.descricao is not None:
        plano.descricao = plan_up.descricao.strip() if plan_up.descricao else None
    if plan_up.ativo is not None:
        plano.ativo = plan_up.ativo

    db.commit()
    db.refresh(plano)

    registrar_auditoria(
        db=db,
        acao="PLANO_DESCONTO_ATUALIZADO",
        entidade="PaymentPlan",
        registro_id=str(plano.id),
        detalhes={"nome": plano.nome, "percentual": plano.percentual_desconto, "ativo": plano.ativo},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return plano


@router.delete("/plans/{plan_id}", status_code=status.HTTP_200_OK, summary="Excluir ou desativar plano/desconto")
def delete_payment_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value)),
):
    plano = db.query(PaymentPlan).filter(PaymentPlan.id == plan_id).first()
    if not plano:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano ou desconto não encontrado.")

    em_uso = db.query(Matricula).filter(Matricula.plano_id == plan_id).count()
    if plano.padrao or em_uso > 0:
        plano.ativo = False
        db.commit()
        msg = f"Plano/desconto '{plano.nome}' desativado com sucesso (preservando matrículas ou política base)."
    else:
        db.delete(plano)
        db.commit()
        msg = f"Plano/desconto '{plano.nome}' excluído com sucesso."

    registrar_auditoria(
        db=db,
        acao="PLANO_DESCONTO_EXCLUIDO",
        entidade="PaymentPlan",
        registro_id=str(plan_id),
        detalhes={"acao": msg},
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return {"status": "ok", "mensagem": msg}


@router.put("/course-rules", response_model=CourseDiscountRuleResponse, summary="Configurar regra de plano/desconto por curso")
def upsert_course_discount_rule(
    rule_in: CourseDiscountRuleUpsert,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value)),
):
    curso = db.query(Course).filter(Course.id == rule_in.curso_id).first()
    if not curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado.")
    plano = db.query(PaymentPlan).filter(PaymentPlan.id == rule_in.plano_id).first()
    if not plano:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano/desconto não encontrado.")

    regra = db.query(CourseDiscountRule).filter(
        CourseDiscountRule.curso_id == rule_in.curso_id,
        CourseDiscountRule.plano_id == rule_in.plano_id,
    ).first()

    if not regra:
        regra = CourseDiscountRule(
            curso_id=rule_in.curso_id,
            plano_id=rule_in.plano_id,
            permitido=rule_in.permitido,
            percentual_override=rule_in.percentual_override,
        )
        db.add(regra)
    else:
        regra.permitido = rule_in.permitido
        regra.percentual_override = rule_in.percentual_override

    db.commit()
    db.refresh(regra)

    registrar_auditoria(
        db=db,
        acao="REGRA_DESCONTO_CURSO_ATUALIZADA",
        entidade="CourseDiscountRule",
        registro_id=str(regra.id),
        detalhes={
            "curso": curso.nome,
            "plano": plano.nome,
            "permitido": regra.permitido,
            "percentual_override": regra.percentual_override,
        },
        usuario=current_user,
        ip=request.client.host if request.client else None,
    )
    return _format_rule(regra)


@router.post("/simulate", response_model=DiscountSimulateResponse, summary="Simular política de planos e descontos")
def simulate_discount_policy(
    sim_in: DiscountSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return simular_politica_desconto(
        db=db,
        curso_id=sim_in.curso_id,
        valor_mensalidade=sim_in.valor_mensalidade,
        duracao_contrato_meses=sim_in.duracao_contrato_meses,
        condicao_pagamento=sim_in.condicao_pagamento.value,
        quantidade_parcelas=sim_in.quantidade_parcelas,
        plano_id=sim_in.plano_id,
        descontos_ids=sim_in.descontos_ids,
        desconto_valor_fixo=sim_in.desconto_valor_fixo,
    )
