from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.discount_policy import (
    PaymentPlan,
    CourseDiscountRule,
    DiscountSettings,
    TipoPoliticaDesconto,
    CondicaoPagamento,
)


DEFAULT_PLANS = [
    {
        "codigo": "A_VISTA",
        "nome": "À Vista",
        "tipo": TipoPoliticaDesconto.PLANO.value,
        "condicao_pagamento": CondicaoPagamento.A_VISTA.value,
        "percentual_desconto": 10.0,
        "meses_minimos": 1,
        "descricao": "Pagamento único integral no ato da matrícula",
        "padrao": True,
    },
    {
        "codigo": "MENSAL",
        "nome": "Mensal",
        "tipo": TipoPoliticaDesconto.PLANO.value,
        "condicao_pagamento": CondicaoPagamento.MENSAL.value,
        "percentual_desconto": 0.0,
        "meses_minimos": 1,
        "descricao": "Cobrança mensal durante a duração do contrato",
        "padrao": True,
    },
    {
        "codigo": "TRIMESTRAL",
        "nome": "Trimestral",
        "tipo": TipoPoliticaDesconto.PLANO.value,
        "condicao_pagamento": CondicaoPagamento.PARCELADO.value,
        "percentual_desconto": 5.0,
        "meses_minimos": 3,
        "descricao": "Plano trimestral (mínimo 3 meses)",
        "padrao": True,
    },
    {
        "codigo": "SEMESTRAL",
        "nome": "Semestral",
        "tipo": TipoPoliticaDesconto.PLANO.value,
        "condicao_pagamento": CondicaoPagamento.PARCELADO.value,
        "percentual_desconto": 8.0,
        "meses_minimos": 6,
        "descricao": "Plano semestral (mínimo 6 meses)",
        "padrao": True,
    },
    {
        "codigo": "ANUAL",
        "nome": "Anual",
        "tipo": TipoPoliticaDesconto.PLANO.value,
        "condicao_pagamento": CondicaoPagamento.PARCELADO.value,
        "percentual_desconto": 10.0,
        "meses_minimos": 12,
        "descricao": "Plano anual (mínimo 12 meses)",
        "padrao": True,
    },
    {
        "codigo": "IRMAO",
        "nome": "Irmão (Família)",
        "tipo": TipoPoliticaDesconto.DESCONTO.value,
        "condicao_pagamento": None,
        "percentual_desconto": 10.0,
        "meses_minimos": None,
        "descricao": "Desconto familiar para irmãos matriculados",
        "padrao": True,
    },
    {
        "codigo": "INDICACAO",
        "nome": "Indicação",
        "tipo": TipoPoliticaDesconto.DESCONTO.value,
        "condicao_pagamento": None,
        "percentual_desconto": 5.0,
        "meses_minimos": None,
        "descricao": "Desconto por indicação de aluno",
        "padrao": True,
    },
]


def ensure_default_discount_policies(db: Session) -> DiscountSettings:
    """Garante a existência das configurações globais e dos planos padrão sem sobrescrever edições existentes."""
    settings_row = db.query(DiscountSettings).filter(DiscountSettings.id == 1).first()
    created = False
    if not settings_row:
        settings_row = DiscountSettings(id=1, teto_maximo_desconto_percentual=30.0)
        db.add(settings_row)
        created = True

    existing_codes = {p.codigo for p in db.query(PaymentPlan.codigo).all()}
    for item in DEFAULT_PLANS:
        if item["codigo"] not in existing_codes:
            db.add(PaymentPlan(**item, ativo=True))
            created = True

    if created:
        db.commit()
        db.refresh(settings_row)
    return settings_row


def _percentual_efetivo_plano(
    db: Session,
    plano: PaymentPlan,
    curso_id: Optional[int],
) -> Dict[str, Any]:
    if not plano.ativo:
        return {"percentual": 0.0, "permitido": False, "motivo": "Inativo"}
    if curso_id is not None:
        regra = db.query(CourseDiscountRule).filter(
            CourseDiscountRule.curso_id == curso_id,
            CourseDiscountRule.plano_id == plano.id,
        ).first()
        if regra:
            if not regra.permitido:
                return {"percentual": 0.0, "permitido": False, "motivo": "Bloqueado para o curso"}
            if regra.percentual_override is not None:
                return {"percentual": float(regra.percentual_override), "permitido": True, "motivo": "Regra do curso"}
    return {"percentual": float(plano.percentual_desconto or 0.0), "permitido": True, "motivo": "Política padrão"}


def simular_politica_desconto(
    db: Session,
    *,
    curso_id: Optional[int],
    valor_mensalidade: float,
    duracao_contrato_meses: int,
    condicao_pagamento: str,
    quantidade_parcelas: Optional[int],
    plano_id: Optional[int],
    descontos_ids: List[int],
    desconto_valor_fixo: float = 0.0,
) -> Dict[str, Any]:
    settings_row = ensure_default_discount_policies(db)
    teto = float(settings_row.teto_maximo_desconto_percentual or 30.0)

    itens_aplicados: List[Dict[str, Any]] = []
    desconto_plano_pct = 0.0
    plano_obj: Optional[PaymentPlan] = None

    if plano_id is not None:
        plano_obj = db.query(PaymentPlan).filter(PaymentPlan.id == plano_id).first()
        if plano_obj:
            info = _percentual_efetivo_plano(db, plano_obj, curso_id)
            desconto_plano_pct = info["percentual"]
            itens_aplicados.append({
                "id": plano_obj.id,
                "codigo": plano_obj.codigo,
                "nome": plano_obj.nome,
                "tipo": plano_obj.tipo,
                "percentual": desconto_plano_pct,
                "permitido": info["permitido"],
                "origem": info["motivo"],
            })

    desconto_adicional_pct = 0.0
    if descontos_ids:
        unicos = []
        for did in descontos_ids:
            if did not in unicos and did != plano_id:
                unicos.append(did)
        planos_add = db.query(PaymentPlan).filter(PaymentPlan.id.in_(unicos)).all()
        planos_map = {p.id: p for p in planos_add}
        for did in unicos:
            p = planos_map.get(did)
            if p:
                info = _percentual_efetivo_plano(db, p, curso_id)
                desconto_adicional_pct += info["percentual"]
                itens_aplicados.append({
                    "id": p.id,
                    "codigo": p.codigo,
                    "nome": p.nome,
                    "tipo": p.tipo,
                    "percentual": info["percentual"],
                    "permitido": info["permitido"],
                    "origem": info["motivo"],
                })

    soma_sem_teto = round(desconto_plano_pct + desconto_adicional_pct, 2)
    percentual_aplicado = round(min(teto, soma_sem_teto), 2)

    duracao = max(1, int(duracao_contrato_meses or 12))
    valor_total_bruto = round(float(valor_mensalidade or 0.0) * duracao, 2)

    if condicao_pagamento == CondicaoPagamento.A_VISTA.value:
        qtd_cobrancas = 1
    elif condicao_pagamento == CondicaoPagamento.PARCELADO.value:
        qtd_cobrancas = min(12, max(1, int(quantidade_parcelas or 1)))
    else:
        qtd_cobrancas = duracao

    fixo = max(0.0, float(desconto_valor_fixo or 0.0))
    desconto_pct_reais = round(valor_total_bruto * (percentual_aplicado / 100.0), 2)
    desconto_total_reais = min(valor_total_bruto, round(desconto_pct_reais + fixo, 2))
    valor_total_liquido = round(max(0.0, valor_total_bruto - desconto_total_reais), 2)
    valor_por_cobranca = round(valor_total_liquido / qtd_cobrancas, 2)

    return {
        "plano_nome": plano_obj.nome if plano_obj else None,
        "valor_total_bruto": valor_total_bruto,
        "desconto_plano_percentual": round(desconto_plano_pct, 2),
        "desconto_adicional_percentual": round(desconto_adicional_pct, 2),
        "percentual_soma_sem_teto": soma_sem_teto,
        "teto_maximo_percentual": teto,
        "percentual_aplicado": percentual_aplicado,
        "desconto_valor_fixo": round(fixo, 2),
        "desconto_total_reais": desconto_total_reais,
        "valor_total_liquido": valor_total_liquido,
        "quantidade_cobrancas": qtd_cobrancas,
        "valor_por_cobranca": valor_por_cobranca,
        "itens_aplicados": itens_aplicados,
    }
