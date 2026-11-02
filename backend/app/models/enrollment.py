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


class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="RESTRICT"), nullable=False, index=True)
    turma_id = Column(Integer, ForeignKey("class_groups.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(String(30), nullable=False, default=StatusMatricula.ATIVA.value, index=True)

    # Datas do contrato
    data_matricula = Column(Date, nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_termino_previsto = Column(Date, nullable=True)

    # Contrato (renovação NÃO é automática — exige contrato assinado)
    numero_contrato = Column(String(50), nullable=True, unique=True, index=True)
    contrato_assinado = Column(Boolean, default=False, nullable=False)
    data_assinatura_contrato = Column(DateTime, nullable=True)

    # Valores
    valor_mensalidade = Column(Float, nullable=False)
    desconto_percentual = Column(Float, default=0.0, nullable=False)  # ex: 10.0 para 10%
    tipo_desconto = Column(String(50), nullable=True)  # irmao, indicacao, bolsa

    # Trancamento/Cancelamento
    motivo_cancelamento = Column(Text, nullable=True)
    data_cancelamento = Column(DateTime, nullable=True)
    multa_cancelamento = Column(Float, default=0.0, nullable=False)

    # Aula experimental
    aula_experimental = Column(Boolean, default=False, nullable=False)

    observacoes = Column(Text, nullable=True)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    aluno = relationship("Aluno", back_populates="matriculas")
    turma = relationship("ClassGroup")

    def __repr__(self) -> str:
        return f"<Matricula id={self.id} aluno_id={self.aluno_id} turma_id={self.turma_id} status='{self.status}'>"
