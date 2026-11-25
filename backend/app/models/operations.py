from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class ModalidadePagamentoProfessor(str, enum.Enum):
    POR_PRESENCA = "POR_PRESENCA"
    PERCENTUAL = "PERCENTUAL"
    FIXO_MENSAL = "FIXO_MENSAL"


class ModoPagamentoPercentual(str, enum.Enum):
    UNICO = "UNICO"
    PARCELADO_MENSAL = "PARCELADO_MENSAL"


class StatusFechamento(str, enum.Enum):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"
    PAGO_PARCIAL = "PAGO_PARCIAL"
    PAGO = "PAGO"


class TeacherPaymentRule(Base):
    """Regra de remuneração configurável por professor e por curso."""
    __tablename__ = "teacher_payment_rules"
    __table_args__ = (
        UniqueConstraint("professor_id", "curso_id", name="uq_prof_curso_regra_pag"),
    )

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)

    modalidade = Column(String(30), nullable=False, default=ModalidadePagamentoProfessor.POR_PRESENCA.value)
    valor_por_presenca = Column(Float, default=0.0, nullable=False)
    percentual_curso = Column(Float, default=0.0, nullable=False)
    pagamento_percentual_modo = Column(String(30), default=ModoPagamentoPercentual.PARCELADO_MENSAL.value, nullable=False)
    valor_fixo_mensal = Column(Float, default=0.0, nullable=False)
    pagar_experimental = Column(Boolean, default=False, nullable=False)
    pagar_cortesia = Column(Boolean, default=False, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    professor = relationship("Teacher")
    curso = relationship("Course")


class TeacherClosing(Base):
    """Fechamento mensal de pagamento por professor."""
    __tablename__ = "teacher_closings"
    __table_args__ = (
        UniqueConstraint("professor_id", "competencia", name="uq_prof_competencia_fechamento"),
    )

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    competencia = Column(String(7), nullable=False, index=True)  # YYYY-MM

    total_aulas_dadas = Column(Integer, default=0, nullable=False)
    total_presencas = Column(Integer, default=0, nullable=False)
    valor_por_presenca_total = Column(Float, default=0.0, nullable=False)
    valor_percentual_total = Column(Float, default=0.0, nullable=False)
    valor_fixo_total = Column(Float, default=0.0, nullable=False)
    valor_total = Column(Float, default=0.0, nullable=False)

    valor_pago = Column(Float, default=0.0, nullable=False)
    saldo_a_pagar = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default=StatusFechamento.FECHADO.value, nullable=False, index=True)
    data_pagamento = Column(Date, nullable=True)
    forma_pagamento = Column(String(20), nullable=True)
    conciliado_extrato = Column(Boolean, default=False, nullable=False)
    referencia_extrato = Column(String(120), nullable=True)

    detalhes_json = Column(Text, nullable=True)  # Detalhado por curso, turma e aluno
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    professor = relationship("Teacher")
    expense = relationship("Expense")


class AttendanceChangeLog(Base):
    """Histórico de alterações na chamada (especialmente quando há justificativa após fechamento)."""
    __tablename__ = "attendance_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_id = Column(Integer, ForeignKey("attendances.id", ondelete="SET NULL"), nullable=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False)
    status_anterior = Column(String(20), nullable=True)
    status_novo = Column(String(20), nullable=False)
    alterado_por_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    alterado_por_nome = Column(String(150), nullable=True)
    motivo = Column(Text, nullable=True)
    competencia = Column(String(7), nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class CommercialConfig(Base):
    """Configuração de remuneração do Comercial."""
    __tablename__ = "commercial_configs"

    id = Column(Integer, primary_key=True, default=1)
    nome_responsavel = Column(String(150), default="Comercial HB", nullable=False)
    valor_fixo_mensal = Column(Float, default=0.0, nullable=False)
    comissao_por_matricula = Column(Float, default=0.0, nullable=False)
    percentual_sobre_vendas = Column(Float, default=0.0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CommercialPayout(Base):
    """Fechamento mensal de pagamento do Comercial."""
    __tablename__ = "commercial_payouts"
    __table_args__ = (
        UniqueConstraint("competencia", name="uq_comercial_competencia"),
    )

    id = Column(Integer, primary_key=True, index=True)
    competencia = Column(String(7), nullable=False, index=True)
    nome_responsavel = Column(String(150), nullable=False)
    qtd_matriculas_novas = Column(Integer, default=0, nullable=False)
    total_vendas_mes = Column(Float, default=0.0, nullable=False)

    valor_fixo = Column(Float, default=0.0, nullable=False)
    valor_comissao_matriculas = Column(Float, default=0.0, nullable=False)
    valor_percentual_vendas = Column(Float, default=0.0, nullable=False)
    total_devido = Column(Float, default=0.0, nullable=False)

    valor_pago = Column(Float, default=0.0, nullable=False)
    saldo = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="EM_ABERTO", nullable=False)
    data_pagamento = Column(Date, nullable=True)
    forma_pagamento = Column(String(20), nullable=True)
    observacoes = Column(Text, nullable=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class WorkshopSession(Base):
    """Sessões/Workshops do Ateliê - Parceria (ex.: Esmaltação em Cerâmica, Modelagem em Argila)."""
    __tablename__ = "workshop_sessions"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    modalidade = Column(String(100), nullable=False)
    professora_parceira = Column(String(150), nullable=False)
    data_realizacao = Column(Date, nullable=False, index=True)
    competencia = Column(String(7), nullable=False, index=True)  # YYYY-MM
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    centro_custo_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True)

    percentual_escola = Column(Float, default=50.0, nullable=False)
    percentual_professora = Column(Float, default=50.0, nullable=False)
    despesas_materiais = Column(Float, default=0.0, nullable=False)

    repasse_pago = Column(Boolean, default=False, nullable=False)
    data_repasse = Column(Date, nullable=True)
    forma_repasse = Column(String(20), nullable=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    participantes = relationship("WorkshopParticipant", back_populates="workshop", cascade="all, delete-orphan")
    curso = relationship("Course")
    centro_custo = relationship("CostCenter")


class WorkshopParticipant(Base):
    """Alunos avulsos participantes de cada data/workshop de parceria."""
    __tablename__ = "workshop_participants"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshop_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="SET NULL"), nullable=True)
    aluno_nome = Column(String(150), nullable=False)
    telefone = Column(String(30), nullable=True)
    valor_pago = Column(Float, nullable=False)
    forma_pagamento = Column(String(20), nullable=False, default="PIX")
    observacoes = Column(String(255), nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    workshop = relationship("WorkshopSession", back_populates="participantes")
