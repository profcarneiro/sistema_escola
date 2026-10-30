from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class FaixaEtaria(str, enum.Enum):
    INFANTIL = "INFANTIL"          # 7 a 10 anos
    JUVENIL = "JUVENIL"            # 11 a 17 anos
    ADULTO = "ADULTO"              # 18 a 65 anos
    TERCEIRA_IDADE = "TERCEIRA_IDADE"  # 65+ anos


class DiaSemana(str, enum.Enum):
    SEGUNDA = "SEGUNDA"
    TERCA = "TERCA"
    QUARTA = "QUARTA"
    QUINTA = "QUINTA"
    SEXTA = "SEXTA"
    SABADO = "SABADO"
    DOMINGO = "DOMINGO"


class Turno(str, enum.Enum):
    MANHA = "MANHA"
    TARDE = "TARDE"
    NOITE = "NOITE"


class ClassGroup(Base):
    __tablename__ = "class_groups"
    __table_args__ = (
        CheckConstraint("capacidade_maxima <= 9", name="check_turma_capacidade_maxima_9"),
        CheckConstraint("capacidade_maxima >= 1", name="check_turma_capacidade_minima_1"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    curso_id = Column(Integer, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False)
    sala_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    professor_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    
    faixa_etaria = Column(String(30), nullable=False, default=FaixaEtaria.ADULTO.value)
    dia_semana = Column(String(20), nullable=False)
    turno = Column(String(20), nullable=False)
    horario_inicio = Column(String(5), nullable=False)  # Formato "HH:MM", ex: "09:00"
    horario_fim = Column(String(5), nullable=False)     # Formato "HH:MM", ex: "11:00"
    
    capacidade_maxima = Column(Integer, default=9, nullable=False)
    ativa = Column(Boolean, default=True, nullable=False)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    curso = relationship("Course", back_populates="turmas")
    sala = relationship("Room", back_populates="turmas")
    professor = relationship("Teacher", back_populates="turmas")

    def __repr__(self) -> str:
        return f"<ClassGroup id={self.id} nome='{self.nome}' dia={self.dia_semana} {self.horario_inicio}-{self.horario_fim}>"
