from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.financial import FormaPagamento
from app.models.operations import (
    ModalidadePagamentoProfessor,
    ModoPagamentoPercentual,
    StatusFechamento,
)


# ─── Pagamento de Professores ─────────────────────────────────────────────────

class TeacherPaymentRuleUpsert(BaseModel):
    professor_id: int
    curso_id: Optional[int] = None
    modalidade: ModalidadePagamentoProfessor = ModalidadePagamentoProfessor.POR_PRESENCA
    valor_por_presenca: float = Field(0.0, ge=0.0)
    percentual_curso: float = Field(0.0, ge=0.0, le=100.0)
    pagamento_percentual_modo: ModoPagamentoPercentual = ModoPagamentoPercentual.PARCELADO_MENSAL
    valor_fixo_mensal: float = Field(0.0, ge=0.0)
    pagar_experimental: bool = False
    pagar_cortesia: bool = False
    ativo: bool = True


class TeacherPaymentRuleResponse(TeacherPaymentRuleUpsert):
    id: int
    professor_nome: Optional[str] = None
    curso_nome: Optional[str] = None
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class TeacherClosingGenerateRequest(BaseModel):
    competencia: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    professor_id: Optional[int] = None


class TeacherClosingPayRequest(BaseModel):
    valor_pago: float = Field(..., gt=0.0)
    data_pagamento: date
    forma_pagamento: FormaPagamento
    conciliado_extrato: bool = False
    referencia_extrato: Optional[str] = Field(None, max_length=120)
    observacoes: Optional[str] = None


class TeacherClosingResponse(BaseModel):
    id: int
    professor_id: int
    professor_nome: Optional[str] = None
    competencia: str
    total_aulas_dadas: int
    total_presencas: int
    valor_por_presenca_total: float
    valor_percentual_total: float
    valor_fixo_total: float
    valor_total: float
    valor_pago: float
    saldo_a_pagar: float
    status: StatusFechamento
    data_pagamento: Optional[date] = None
    forma_pagamento: Optional[str] = None
    conciliado_extrato: bool
    referencia_extrato: Optional[str] = None
    detalhes: List[Any] = Field(default_factory=list)
    expense_id: Optional[int] = None
    observacoes: Optional[str] = None
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Pagamento do Comercial ───────────────────────────────────────────────────

class CommercialConfigUpdate(BaseModel):
    nome_responsavel: str = Field(..., min_length=2, max_length=150)
    valor_fixo_mensal: float = Field(0.0, ge=0.0)
    comissao_por_matricula: float = Field(0.0, ge=0.0)
    percentual_sobre_vendas: float = Field(0.0, ge=0.0, le=100.0)
    ativo: bool = True


class CommercialConfigResponse(CommercialConfigUpdate):
    id: int
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class CommercialClosingPayRequest(BaseModel):
    valor_pago: float = Field(..., gt=0.0)
    data_pagamento: date
    forma_pagamento: FormaPagamento
    observacoes: Optional[str] = None


class CommercialPayoutResponse(BaseModel):
    id: int
    competencia: str
    nome_responsavel: str
    qtd_matriculas_novas: int
    total_vendas_mes: float
    valor_fixo: float
    valor_comissao_matriculas: float
    valor_percentual_vendas: float
    total_devido: float
    valor_pago: float
    saldo: float
    status: str
    data_pagamento: Optional[date] = None
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None
    expense_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Ateliê - Parceria (Workshops e Alunos Avulsos) ───────────────────────────

class WorkshopParticipantCreate(BaseModel):
    aluno_id: Optional[int] = None
    aluno_nome: str = Field(..., min_length=2, max_length=150)
    telefone: Optional[str] = Field(None, max_length=30)
    valor_pago: float = Field(..., ge=0.0)
    forma_pagamento: FormaPagamento = FormaPagamento.PIX
    observacoes: Optional[str] = Field(None, max_length=255)


class WorkshopParticipantResponse(WorkshopParticipantCreate):
    id: int
    workshop_id: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkshopSessionCreate(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=150)
    modalidade: str = Field(..., min_length=2, max_length=100)
    professora_parceira: str = Field(..., min_length=2, max_length=150)
    data_realizacao: date
    curso_id: Optional[int] = None
    percentual_escola: float = Field(50.0, ge=0.0, le=100.0)
    percentual_professora: float = Field(50.0, ge=0.0, le=100.0)
    despesas_materiais: float = Field(0.0, ge=0.0)
    observacoes: Optional[str] = None
    participantes: List[WorkshopParticipantCreate] = Field(default_factory=list)


class WorkshopPayTransferRequest(BaseModel):
    data_repasse: date
    forma_repasse: FormaPagamento


class WorkshopSessionResponse(BaseModel):
    id: int
    titulo: str
    modalidade: str
    professora_parceira: str
    data_realizacao: date
    competencia: str
    curso_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    percentual_escola: float
    percentual_professora: float
    despesas_materiais: float
    repasse_pago: bool
    data_repasse: Optional[date] = None
    forma_repasse: Optional[str] = None
    observacoes: Optional[str] = None
    receita_bruta: float = 0.0
    parte_escola: float = 0.0
    valor_repassar_professora: float = 0.0
    resultado_escola: float = 0.0
    participantes: List[WorkshopParticipantResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkshopMonthlySummaryResponse(BaseModel):
    competencia: str
    total_sessoes: int
    total_participantes: int
    receita_total: float
    despesas_materiais_total: float
    parte_escola_total: float
    valor_repassar_total: float
    valor_ja_repassado: float
    saldo_a_repassar: float
    resultado_liquido_escola: float
