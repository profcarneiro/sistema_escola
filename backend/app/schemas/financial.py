from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.financial import FormaPagamento, StatusTitulo, SituacaoDespesa, TipoCentroCusto


FORMAS_PAGAMENTO_VALIDAS = [f.value for f in FormaPagamento]


class PaymentCreate(BaseModel):
    valor_pago: float = Field(..., gt=0.0, description="Valor efetivamente pago")
    forma_pagamento: FormaPagamento = Field(..., description="Forma de pagamento: PIX, CARTAO, BOLETO, DINHEIRO, TRANSFERENCIA")
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
    valor_nominal: float = Field(..., ge=0.0, description="Valor nominal sem descontos")
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


class CostCenterBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    tipo: TipoCentroCusto = TipoCentroCusto.GERAL
    curso_id: Optional[int] = None


class CostCenterCreate(CostCenterBase):
    codigo: Optional[str] = Field(None, max_length=60)


class CostCenterResponse(CostCenterBase):
    id: int
    codigo: str
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class CostCenterMonthMetrics(BaseModel):
    competencia: str
    receita_prevista: float
    custo_previsto: float
    resultado_previsto: float
    receita_realizada: float
    custo_realizado: float
    resultado_realizado: float


class CostCenterReportItem(BaseModel):
    centro_custo_id: int
    nome: str
    tipo: str
    curso_id: Optional[int] = None
    receita_prevista_total: float
    custo_previsto_total: float
    resultado_previsto_total: float
    percentual_receita_prevista: float
    receita_realizada_total: float
    custo_realizado_total: float
    resultado_realizado_total: float
    percentual_receita_realizada: float
    meses: List[CostCenterMonthMetrics] = []


class CostCenterReportResponse(BaseModel):
    total_receita_prevista: float
    total_custo_previsto: float
    total_resultado_previsto: float
    total_receita_realizada: float
    total_custo_realizado: float
    total_resultado_realizado: float
    centros: List[CostCenterReportItem]


class ExpenseBase(BaseModel):
    categoria: str = Field(..., min_length=2, max_length=100, description="Categoria: Aluguel, Água, Luz, Material, etc.")
    descricao: str = Field(..., min_length=2, max_length=255, description="Descrição do gasto")
    valor: Optional[float] = Field(None, gt=0.0, description="Valor da despesa em R$")
    valor_previsto: Optional[float] = Field(None, gt=0.0, description="Valor previsto da despesa em R$")
    valor_pago: Optional[float] = Field(None, ge=0.0, description="Valor efetivamente pago em R$")
    data_competencia: date = Field(..., description="Data de competência da despesa")
    data_vencimento: Optional[date] = Field(None, description="Data de vencimento")
    data_pagamento: Optional[date] = Field(None, description="Data em que o pagamento foi realizado")
    pago: Optional[bool] = Field(None, description="Indica se a despesa já foi quitada")
    situacao: Optional[SituacaoDespesa] = Field(None, description="EM_ABERTO ou PAGO")
    forma_pagamento: FormaPagamento = Field(FormaPagamento.PIX, description="Forma de pagamento utilizada")
    centro_custo_id: Optional[int] = Field(None, description="Centro de custo vinculado")
    comprovante: Optional[str] = Field(None, description="Número do recibo ou nota fiscal")
    observacoes: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    recorrente: bool = False
    recorrencia_meses: int = Field(1, ge=1, le=36)
    total_parcelas: int = Field(1, ge=1, le=36)


class ExpenseUpdate(BaseModel):
    categoria: Optional[str] = Field(None, min_length=2, max_length=100)
    descricao: Optional[str] = Field(None, min_length=2, max_length=255)
    valor_previsto: Optional[float] = Field(None, gt=0.0)
    valor_pago: Optional[float] = Field(None, ge=0.0)
    data_competencia: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    pago: Optional[bool] = None
    situacao: Optional[SituacaoDespesa] = None
    forma_pagamento: Optional[FormaPagamento] = None
    centro_custo_id: Optional[int] = None
    comprovante: Optional[str] = None
    observacoes: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    categoria: str
    descricao: str
    valor: float
    valor_previsto: Optional[float] = None
    valor_pago: float = 0.0
    data_competencia: date
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    pago: bool
    situacao: str = "EM_ABERTO"
    forma_pagamento: FormaPagamento
    centro_custo_id: Optional[int] = None
    centro_custo_nome: Optional[str] = None
    recorrente: bool = False
    parcela_atual: Optional[int] = None
    total_parcelas: Optional[int] = None
    parcelas_criadas: int = 1
    comprovante: Optional[str] = None
    observacoes: Optional[str] = None
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


class DiscountReportByTypeItem(BaseModel):
    tipo: str
    quantidade_faturas: int
    quantidade_matriculas: int
    total_desconto: float


class DiscountReportByMonthItem(BaseModel):
    competencia: str
    quantidade_faturas: int
    total_bruto: float
    total_desconto: float
    total_liquido: float


class DiscountManualAuditItem(BaseModel):
    matricula_id: int
    aluno_nome: str
    turma_nome: str
    plano_nome: Optional[str] = None
    desconto_percentual: float
    desconto_valor_fixo: float
    alterado_por: Optional[str] = None
    motivo: Optional[str] = None
    alterado_em: Optional[datetime] = None


class DiscountsReportResponse(BaseModel):
    total_descontos_concedidos: float
    total_faturas_com_desconto: int
    por_tipo: List[DiscountReportByTypeItem]
    por_mes: List[DiscountReportByMonthItem]
    alteracoes_manuais: List[DiscountManualAuditItem]


# ─── Visões Gerenciais: Fluxo Mês a Mês, Previsão 12 Meses e Matriz Aluno ──────

class MonthlyCashFlowItem(BaseModel):
    competencia: str
    mensalidades_recebidas: float
    receitas_workshops: float = 0.0
    total_entradas: float
    pagamentos_professores: float
    pagamento_comercial: float
    despesas_por_categoria: Dict[str, float]
    total_despesas_categorias: float
    total_saidas: float
    saldo_mes: float
    saldo_acumulado: float


class MonthlyCashFlowResponse(BaseModel):
    ano: int
    categorias_despesas: List[str]
    total_entradas_ano: float
    total_professores_ano: float
    total_comercial_ano: float
    total_despesas_ano: float
    total_saidas_ano: float
    resultado_caixa_ano: float
    meses: List[MonthlyCashFlowItem]


class ForecastSettingsUpdate(BaseModel):
    novos_alunos_mes: int = Field(2, ge=0, le=200)
    saidas_alunos_mes: int = Field(0, ge=0, le=200)
    custo_fixo_mensal_estimado: float = Field(0.0, ge=0.0)
    ticket_medio_override: float = Field(0.0, ge=0.0)


class ForecastMonthItem(BaseModel):
    competencia: str
    alunos_ativos_inicio: int
    novos_alunos_previstos: int
    saidas_contratuais: int
    saidas_previstas: int
    alunos_ativos_fim: int
    receita_contratada: float
    receita_prevista: float
    saidas_previstas_valor: float
    resultado_previsto: float
    ponto_equilibrio_alunos: int
    lucro_dani: float
    lucro_helena: float
    receita_realizada: float
    saidas_realizadas: float
    resultado_realizado: float
    variacao_resultado: float


class Forecast12MonthsResponse(BaseModel):
    mes_inicio: str
    alunos_ativos_atual: int
    ticket_medio_referencia: float
    premissas: ForecastSettingsUpdate
    receita_prevista_total: float
    saidas_previstas_total: float
    resultado_previsto_total: float
    lucro_dani_total: float
    lucro_helena_total: float
    receita_realizada_total: float
    saidas_realizadas_total: float
    resultado_realizado_total: float
    meses: List[ForecastMonthItem]


class StudentMonthCell(BaseModel):
    competencia: str
    status: str  # PAGO, PENDENTE, ATRASADO, PARCIAL, CORTESIA, SEM_COBRANCA
    valor_previsto: float
    valor_pago: float
    quantidade_faturas: int
    forma_pagamento: Optional[str] = None


class StudentMonthlyRow(BaseModel):
    aluno_id: int
    aluno_nome: str
    responsavel_nome: Optional[str] = None
    turmas: List[str] = []
    total_previsto_ano: float
    total_pago_ano: float
    celulas: Dict[str, StudentMonthCell]


class StudentMonthlyMatrixResponse(BaseModel):
    ano: int
    meses: List[str]
    totais_previsto_mes: Dict[str, float]
    totais_pago_mes: Dict[str, float]
    alunos: List[StudentMonthlyRow]
