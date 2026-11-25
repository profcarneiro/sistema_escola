from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ListaEspera(Base):
    """
    Lista de espera para turmas que atingiram sua capacidade máxima configurada.
    Quando uma vaga libera, o sistema notifica o próximo da fila.
    """
    __tablename__ = "lista_espera"
    __table_args__ = (
        UniqueConstraint("aluno_id", "turma_id", name="uq_aluno_turma_espera"),
    )

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    turma_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    posicao = Column(Integer, nullable=False)  # ordem na fila
    ativa = Column(Boolean, default=True, nullable=False)
    notificado = Column(Boolean, default=False, nullable=False)
    data_entrada = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    observacoes = Column(String(255), nullable=True)

    aluno = relationship("Aluno", back_populates="lista_espera")
    turma = relationship("ClassGroup")

    def __repr__(self) -> str:
        return f"<ListaEspera aluno_id={self.aluno_id} turma_id={self.turma_id} posicao={self.posicao}>"
