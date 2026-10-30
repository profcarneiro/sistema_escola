from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    nome = Column(String(150), nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    telefone = Column(String(30), nullable=True)
    endereco = Column(String(255), nullable=True)
    especialidades = Column(Text, nullable=True)  # ex: "Aquarela, Óleo sobre tela, Mangá"
    disponibilidade = Column(Text, nullable=True)  # ex: "Quinta manhã, Terça noite, Sábado manhã"
    substituto_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    substituto = relationship("Teacher", remote_side=[id], foreign_keys=[substituto_id])
    turmas = relationship("ClassGroup", back_populates="professor")

    def __repr__(self) -> str:
        return f"<Teacher id={self.id} nome='{self.nome}' email='{self.email}'>"
