from datetime import datetime, date, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False, index=True)
    data_nascimento = Column(Date, nullable=False)
    cpf = Column(String(14), nullable=True, unique=True, index=True)  # Apenas adultos
    email = Column(String(150), nullable=True, index=True)
    telefone = Column(String(30), nullable=True)
    endereco = Column(String(255), nullable=True)
    foto_url = Column(String(255), nullable=True)

    # Saúde e LGPD
    alergias = Column(Text, nullable=True)
    medicacoes = Column(Text, nullable=True)
    observacoes_saude = Column(Text, nullable=True)
    autorizacao_imagem = Column(Boolean, default=False, nullable=False)
    autorizacao_imagem_data = Column(DateTime, nullable=True)

    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relacionamentos
    responsavel = relationship(
        "Responsavel",
        back_populates="aluno",
        uselist=False,  # 1:1 — um aluno tem NO MÁXIMO um responsável
        cascade="save-update, merge"
    )
    matriculas = relationship("Matricula", back_populates="aluno", cascade="save-update, merge")
    lista_espera = relationship("ListaEspera", back_populates="aluno", cascade="save-update, merge")

    def __repr__(self) -> str:
        return f"<Aluno id={self.id} nome='{self.nome}' nascimento={self.data_nascimento}>"
