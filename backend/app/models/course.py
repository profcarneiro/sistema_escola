from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    duracao_meses = Column(Integer, nullable=True, default=12)
    valor_mensalidade = Column(Float, nullable=False, default=250.0)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    turmas = relationship("ClassGroup", back_populates="curso")

    def __repr__(self) -> str:
        return f"<Course id={self.id} nome='{self.nome}'>"
