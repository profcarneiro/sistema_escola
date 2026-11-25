from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class TipoPoliticaDesconto(str, enum.Enum):
    PLANO = "PLANO"
    DESCONTO = "DESCONTO"


class CondicaoPagamento(str, enum.Enum):
    A_VISTA = "A_VISTA"
    PARCELADO = "PARCELADO"
    MENSAL = "MENSAL"


class PaymentPlan(Base):
    """Planos de pagamento e políticas de desconto configuráveis pela direção."""
    __tablename__ = "payment_plans"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(30), nullable=False, default=TipoPoliticaDesconto.PLANO.value)  # PLANO ou DESCONTO
    condicao_pagamento = Column(String(20), nullable=True)  # A_VISTA, PARCELADO, MENSAL (para PLANO)
    percentual_desconto = Column(Float, default=0.0, nullable=False)
    meses_minimos = Column(Integer, nullable=True)
    descricao = Column(String(255), nullable=True)
    padrao = Column(Boolean, default=False, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    regras_cursos = relationship("CourseDiscountRule", back_populates="plano", cascade="all, delete-orphan")


class CourseDiscountRule(Base):
    """Regras específicas de desconto por curso (ex.: curso sem desconto à vista ou % próprio)."""
    __tablename__ = "course_discount_rules"
    __table_args__ = (
        UniqueConstraint("curso_id", "plano_id", name="uq_curso_plano_regra"),
    )

    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    plano_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    permitido = Column(Boolean, default=True, nullable=False)
    percentual_override = Column(Float, nullable=True)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    curso = relationship("Course")
    plano = relationship("PaymentPlan", back_populates="regras_cursos")


class DiscountSettings(Base):
    """Configurações globais de teto máximo de descontos cumulativos."""
    __tablename__ = "discount_settings"

    id = Column(Integer, primary_key=True, default=1)
    teto_maximo_desconto_percentual = Column(Float, default=30.0, nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    atualizado_por_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
