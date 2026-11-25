from datetime import datetime, date, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class FormaPagamento(str, enum.Enum):
    PIX = "PIX"
    CARTAO = "CARTAO"
    BOLETO = "BOLETO"
    DINHEIRO = "DINHEIRO"
    TRANSFERENCIA = "TRANSFERENCIA"


class StatusTitulo(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    ATRASADO = "ATRASADO"
    CANCELADO = "CANCELADO"
    NEGOCIADO = "NEGOCIADO"


class SituacaoDespesa(str, enum.Enum):
    EM_ABERTO = "EM_ABERTO"
    PAGO = "PAGO"


class TipoCentroCusto(str, enum.Enum):
    GERAL = "GERAL"
    CURSO = "CURSO"


class CostCenter(Base):
    """Centros de custo gerais e centros de custo vinculados a cada curso."""
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(60), unique=True, nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    tipo = Column(String(20), nullable=False, default=TipoCentroCusto.GERAL.value)  # GERAL ou CURSO
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    curso = relationship("Course")

    def __repr__(self) -> str:
        return f"<CostCenter id={self.id} codigo='{self.codigo}' nome='{self.nome}'>"


class Invoice(Base):
    """
    Título / Mensalidade a receber de um aluno/matrícula.
    Cobrança vinculada preferencialmente ao responsável financeiro.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    matricula_id = Column(Integer, ForeignKey("matriculas.id", ondelete="RESTRICT"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="RESTRICT"), nullable=False, index=True)
    responsavel_id = Column(Integer, ForeignKey("responsaveis.id", ondelete="SET NULL"), nullable=True, index=True)
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    centro_custo_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True, index=True)

    descricao = Column(String(200), nullable=False)  # ex: "Mensalidade 11/2026 - Aquarela"
    competencia = Column(String(7), nullable=False, index=True)  # ex: "2026-11"
    valor_nominal = Column(Float, nullable=False)
    desconto_aplicado = Column(Float, default=0.0, nullable=False)
    valor_final = Column(Float, nullable=False)

    data_vencimento = Column(Date, nullable=False, index=True)
    data_pagamento = Column(DateTime, nullable=True)
    forma_pagamento = Column(String(20), nullable=True)  # PIX, CARTAO, BOLETO, DINHEIRO, TRANSFERENCIA
    status = Column(String(20), default=StatusTitulo.PENDENTE.value, nullable=False, index=True)
    juros_multa = Column(Float, default=0.0, nullable=False)

    codigo_barras_pix = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    matricula = relationship("Matricula")
    aluno = relationship("Aluno")
    responsavel = relationship("Responsavel")
    curso = relationship("Course")
    centro_custo = relationship("CostCenter")
    pagamentos = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} desc='{self.descricao}' valor={self.valor_final} status='{self.status}'>"


class Payment(Base):
    """Registro de baixa / recebimento de pagamento efetuado."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    valor_pago = Column(Float, nullable=False)
    forma_pagamento = Column(String(20), nullable=False)  # PIX, CARTAO, BOLETO, DINHEIRO, TRANSFERENCIA
    data_pagamento = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    comprovante_transacao = Column(String(100), nullable=True)
    recebido_por_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    observacoes = Column(String(255), nullable=True)

    invoice = relationship("Invoice", back_populates="pagamentos")
    recebido_por = relationship("User")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} invoice_id={self.invoice_id} valor={self.valor_pago} forma='{self.forma_pagamento}'>"


class Expense(Base):
    """Contas a pagar e despesas operacionais da Escola para conciliação, centros de custo e DRE."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)  # valor efetivo (compatibilidade)
    valor_previsto = Column(Float, nullable=True)
    valor_pago = Column(Float, default=0.0, nullable=False)
    data_competencia = Column(Date, nullable=False, index=True)
    data_vencimento = Column(Date, nullable=True, index=True)
    data_pagamento = Column(Date, nullable=True)
    pago = Column(Boolean, default=False, nullable=False)
    situacao = Column(String(20), default=SituacaoDespesa.EM_ABERTO.value, nullable=False, index=True)
    forma_pagamento = Column(String(20), nullable=False, default=FormaPagamento.PIX.value)
    centro_custo_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True, index=True)
    recorrente = Column(Boolean, default=False, nullable=False)
    parcela_atual = Column(Integer, nullable=True)
    total_parcelas = Column(Integer, nullable=True)
    grupo_lancamento = Column(String(60), nullable=True, index=True)
    origem_tipo = Column(String(40), nullable=True)  # TEACHER_CLOSING, COMMERCIAL_PAYOUT, WORKSHOP
    origem_id = Column(Integer, nullable=True)
    comprovante = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    centro_custo = relationship("CostCenter")

    def __repr__(self) -> str:
        return f"<Expense id={self.id} cat='{self.categoria}' valor={self.valor} situacao='{self.situacao}'>"
