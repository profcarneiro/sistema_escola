from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.financial import FormaPagamento, StatusTitulo


FORMAS_PAGAMENTO_VALIDAS = [f.value for f in FormaPagamento]


class PaymentCreate(BaseModel):
    valor_pago: float = Field(..., gt=0.0, description="Valor efetivamente pago")
    forma_pagamento: FormaPagamento = Field(..., description="Forma de pagamento: PIX, CARTAO, BOLETO, DINHEIRO")
    comprovante_transacao: Optional[str] = Field(None, max_length=100, description="Código de autorização, NSU ou comprovante")
    observacoes: Optional[str] = Field(None, max_length=255)


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    valor_pago: float
    forma_pagamento: FormaPagamento
    data_pagamento: datetime
    comprovante_transacao: Optional[str] = None
    observacoes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    matricula_id: int = Field(..., description="ID da matrícula de referência")
    aluno_id: int = Field(..., description="ID do aluno")
    descricao: str = Field(..., min_length=2, max_length=200, description="Descrição do título, ex: Mensalidade 11/2026")
    competencia: str = Field(..., description="Mês de competência (YYYY-MM), ex: 2026-11")
    valor_nominal: float = Field(..., gt=0.0, description="Valor nominal sem descontos")
    desconto_aplicado: float = Field(0.0, ge=0.0, description="Valor de desconto concedido em R$")
    data_vencimento: date = Field(..., description="Data limite para pagamento sem juros/multa")
    observacoes: Optional[str] = Field(None, description="Observações financeiras")


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    status: Optional[StatusTitulo] = None
    desconto_aplicado: Optional[float] = Field(None, ge=0.0)
    data_vencimento: Optional[date] = None
    juros_multa: Optional[float] = Field(None, ge=0.0)
    observacoes: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: int
    responsavel_id: Optional[int] = None
    valor_final: float
    data_pagamento: Optional[datetime] = None
    forma_pagamento: Optional[FormaPagamento] = None
    status: StatusTitulo
    juros_multa: float
    aluno_nome: Optional[str] = None
    responsavel_nome: Optional[str] = None
    criado_em: datetime
    pagamentos: List[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(BaseModel):
    categoria: str = Field(..., min_length=2, max_length=100, description="Categoria: Materiais Artísticos, Aluguel, etc.")
    descricao: str = Field(..., min_length=2, max_length=255, description="Descrição do gasto")
    valor: float = Field(..., gt=0.0, description="Valor da despesa em R$")
    data_competencia: date = Field(..., description="Data de competência da despesa")
    data_pagamento: Optional[date] = Field(None, description="Data em que o pagamento foi realizado")
    pago: bool = Field(True, description="Indica se a despesa já foi quitada")
    forma_pagamento: FormaPagamento = Field(FormaPagamento.PIX, description="Forma de pagamento utilizada")
    comprovante: Optional[str] = Field(None, description="Número do recibo ou nota fiscal")
    observacoes: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseResponse(ExpenseBase):
    id: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Demonstrativos Financeiros ───────────────────────────────────────────────

class CashFlowSummary(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_entradas: float
    total_saidas: float
    saldo_operacional: float
    entradas_por_forma: Dict[str, float]
    saidas_por_categoria: Dict[str, float]


class DRESummary(BaseModel):
    competencia_inicio: date
    competencia_fim: date
    receita_bruta: float
    deducoes_descontos: float
    receita_liquida: float
    despesas_operacionais: float
    resultado_liquido: float
    despesas_discriminadas: Dict[str, float]
