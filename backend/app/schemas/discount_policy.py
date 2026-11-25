from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.discount_policy import TipoPoliticaDesconto, CondicaoPagamento


class PaymentPlanBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    tipo: TipoPoliticaDesconto = Field(TipoPoliticaDesconto.PLANO)
    condicao_pagamento: Optional[CondicaoPagamento] = None
    percentual_desconto: float = Field(0.0, ge=0.0, le=100.0)
    meses_minimos: Optional[int] = Field(None, ge=1, le=48)
    descricao: Optional[str] = Field(None, max_length=255)


class PaymentPlanCreate(PaymentPlanBase):
    codigo: Optional[str] = Field(None, max_length=50)


class PaymentPlanUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    tipo: Optional[TipoPoliticaDesconto] = None
    condicao_pagamento: Optional[CondicaoPagamento] = None
    percentual_desconto: Optional[float] = Field(None, ge=0.0, le=100.0)
    meses_minimos: Optional[int] = Field(None, ge=1, le=48)
    descricao: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None


class PaymentPlanResponse(PaymentPlanBase):
    id: int
    codigo: str
    padrao: bool
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseDiscountRuleUpsert(BaseModel):
    curso_id: int
    plano_id: int
    permitido: bool = True
    percentual_override: Optional[float] = Field(None, ge=0.0, le=100.0)


class CourseDiscountRuleResponse(BaseModel):
    id: int
    curso_id: int
    plano_id: int
    permitido: bool
    percentual_override: Optional[float] = None
    curso_nome: Optional[str] = None
    plano_nome: Optional[str] = None
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountSettingsUpdate(BaseModel):
    teto_maximo_desconto_percentual: float = Field(..., ge=0.0, le=100.0)


class DiscountSettingsResponse(BaseModel):
    id: int
    teto_maximo_desconto_percentual: float
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountPolicyBundleResponse(BaseModel):
    configuracoes: DiscountSettingsResponse
    planos: List[PaymentPlanResponse]
    regras_cursos: List[CourseDiscountRuleResponse]


class DiscountSimulateRequest(BaseModel):
    curso_id: Optional[int] = None
    valor_mensalidade: float = Field(..., ge=0.0)
    duracao_contrato_meses: int = Field(12, ge=1, le=48)
    condicao_pagamento: CondicaoPagamento = CondicaoPagamento.MENSAL
    quantidade_parcelas: Optional[int] = Field(None, ge=1, le=24)
    plano_id: Optional[int] = None
    descontos_ids: List[int] = Field(default_factory=list)
    desconto_valor_fixo: float = Field(0.0, ge=0.0)


class DiscountSimulateResponse(BaseModel):
    valor_total_bruto: float
    desconto_plano_percentual: float
    desconto_adicional_percentual: float
    percentual_soma_sem_teto: float
    teto_maximo_percentual: float
    percentual_aplicado: float
    desconto_valor_fixo: float
    desconto_total_reais: float
    valor_total_liquido: float
    quantidade_cobrancas: int
    valor_por_cobranca: float
    itens_aplicados: List[dict]
