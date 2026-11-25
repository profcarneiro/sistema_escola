from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class StatusMatricula(str, enum.Enum):
    ATIVA = "ATIVA"
    TRANCADA = "TRANCADA"
    CANCELADA = "CANCELADA"
    AGUARDANDO_RENOVACAO = "AGUARDANDO_RENOVACAO"
    EXPERIMENTAL = "EXPERIMENTAL"


class TipoCortesia(str, enum.Enum):
    CONTRATO_QUITADO = "CONTRATO_QUITADO"
    BOLSA_100 = "BOLSA_100"
    REPOSICAO = "REPOSICAO"


class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="RESTRICT"), nullable=False, index=True)
    turma_id = Column(Integer, ForeignKey("class_groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True, index=True)

    status = Column(String(30), nullable=False, default=StatusMatricula.ATIVA.value, index=True)

    # Datas do contrato
    data_matricula = Column(Date, nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_termino_previsto = Column(Date, nullable=True)
    data_saida = Column(Date, nullable=True)

    # Contrato (renovação NÃO é automática — exige contrato assinado)
    numero_contrato = Column(String(50), nullable=True, unique=True, index=True)
    contrato_assinado = Column(Boolean, default=False, nullable=False)
    data_assinatura_contrato = Column(DateTime, nullable=True)

    # Valores, duração e condição de pagamento
    valor_mensalidade = Column(Float, nullable=False)
    duracao_contrato_meses = Column(Integer, default=12, nullable=False)
    valor_total_contrato = Column(Float, nullable=True)
    condicao_pagamento = Column(String(20), default="MENSAL", nullable=False)  # A_VISTA, PARCELADO, MENSAL
    plano_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="SET NULL"), nullable=True)
    plano_nome = Column(String(100), nullable=True)

    # Descontos (% + R$ + snapshot da política + auditoria de alteração manual)
    desconto_percentual = Column(Float, default=0.0, nullable=False)  # % efetivo aplicado
    desconto_valor_fixo = Column(Float, default=0.0, nullable=False)  # desconto adicional em R$
    desconto_plano_percentual = Column(Float, default=0.0, nullable=False)
    desconto_adicional_percentual = Column(Float, default=0.0, nullable=False)
    descontos_aplicados_json = Column(Text, nullable=True)  # snapshot JSON dos descontos aplicados
    tipo_desconto = Column(String(50), nullable=True)  # irmao, indicacao, bolsa, etc.
    desconto_editado_manualmente = Column(Boolean, default=False, nullable=False)
    desconto_alterado_por_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    desconto_alterado_por_nome = Column(String(150), nullable=True)
    desconto_motivo_alteracao = Column(Text, nullable=True)
    desconto_alterado_em = Column(DateTime, nullable=True)

    dia_vencimento = Column(Integer, default=10, nullable=True)
    quantidade_parcelas = Column(Integer, default=12, nullable=True)

    # Trancamento/Cancelamento
    motivo_cancelamento = Column(Text, nullable=True)
    data_cancelamento = Column(DateTime, nullable=True)
    multa_cancelamento = Column(Float, default=0.0, nullable=False)

    # Aula experimental e Cortesia sem cobrança
    aula_experimental = Column(Boolean, default=False, nullable=False)
    is_cortesia = Column(Boolean, default=False, nullable=False)
    tipo_cortesia = Column(String(40), nullable=True)  # CONTRATO_QUITADO, BOLSA_100, REPOSICAO

    observacoes = Column(Text, nullable=True)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizada_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    aluno = relationship("Aluno", back_populates="matriculas")
    turma = relationship("ClassGroup")
    curso = relationship("Course")
    plano = relationship("PaymentPlan")

    def __repr__(self) -> str:
        return f"<Matricula id={self.id} aluno_id={self.aluno_id} turma_id={self.turma_id} status='{self.status}'>"
