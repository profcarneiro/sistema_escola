from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Responsavel(Base):
    """
    Responsável legal e financeiro do aluno.
    Regra EXPLÍCITA do cliente: Um aluno NÃO pode ter mais de um responsável.
    UniqueConstraint em aluno_id garante esta regra no nível do banco de dados.
    """
    __tablename__ = "responsaveis"
    __table_args__ = (
        UniqueConstraint("aluno_id", name="uq_responsavel_aluno_unico"),
    )

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Dados obrigatórios para menores (campos obrigatórios do briefing)
    nome = Column(String(150), nullable=False, index=True)
    cpf = Column(String(14), nullable=False, index=True)
    telefone = Column(String(30), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    endereco = Column(String(255), nullable=False)

    # Relacionamento financeiro
    responsavel_financeiro = Column(Boolean, default=True, nullable=False)

    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    aluno = relationship("Aluno", back_populates="responsavel")

    def __repr__(self) -> str:
        return f"<Responsavel id={self.id} nome='{self.nome}' aluno_id={self.aluno_id}>"
