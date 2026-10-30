from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacidade <= 9", name="check_capacidade_maxima_9"),
        CheckConstraint("capacidade >= 1", name="check_capacidade_minima_1"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False, index=True)
    capacidade = Column(Integer, default=9, nullable=False)
    descricao = Column(String(255), nullable=True)
    ativa = Column(Boolean, default=True, nullable=False)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    turmas = relationship("ClassGroup", back_populates="sala")

    def __repr__(self) -> str:
        return f"<Room id={self.id} nome='{self.nome}' capacidade={self.capacidade}>"
