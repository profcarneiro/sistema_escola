from datetime import datetime, date, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class StatusPresenca(str, enum.Enum):
    PRESENTE = "PRESENTE"
    FALTA = "FALTA"
    JUSTIFICADA = "JUSTIFICADA"


class StatusReposicao(str, enum.Enum):
    AGENDADA = "AGENDADA"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


class ConceitoAvaliacao(str, enum.Enum):
    EXCELENTE = "EXCELENTE"
    BOM = "BOM"
    REGULAR = "REGULAR"
    EM_DESENVOLVIMENTO = "EM_DESENVOLVIMENTO"


class Lesson(Base):
    """Diário de classe e plano de aula ministrado por uma turma."""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    turma_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    data_aula = Column(Date, nullable=False, index=True)
    tema_aula = Column(String(200), nullable=False)
    conteudo_programatico = Column(Text, nullable=True)
    materiais_utilizados = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    turma = relationship("ClassGroup")
    professor = relationship("Teacher")
    frequencias = relationship("Attendance", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lesson id={self.id} turma_id={self.turma_id} data={self.data_aula}>"


class Attendance(Base):
    """Registro individual de chamada de um aluno em determinada aula."""
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_id = Column(Integer, ForeignKey("matriculas.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=StatusPresenca.PRESENTE.value)
    motivo_justificativa = Column(String(255), nullable=True)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    lesson = relationship("Lesson", back_populates="frequencias")
    aluno = relationship("Aluno")
    matricula = relationship("Matricula")

    def __repr__(self) -> str:
        return f"<Attendance id={self.id} aluno_id={self.aluno_id} status={self.status}>"


class ClassMakeUp(Base):
    """
    Agendamento de reposição de aula.
    REGRA DO BRIEFING: Reposição permitida estritamente dentro do mês corrente ou na 1ª semana do mês seguinte.
    """
    __tablename__ = "class_makeups"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_origem_id = Column(Integer, ForeignKey("matriculas.id", ondelete="CASCADE"), nullable=False)
    attendance_falta_id = Column(Integer, ForeignKey("attendances.id", ondelete="SET NULL"), nullable=True)
    data_falta = Column(Date, nullable=False)
    
    turma_destino_id = Column(Integer, ForeignKey("class_groups.id", ondelete="RESTRICT"), nullable=False)
    data_reposicao = Column(Date, nullable=False)
    status = Column(String(20), default=StatusReposicao.AGENDADA.value, nullable=False)
    observacoes = Column(String(255), nullable=True)
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    aluno = relationship("Aluno")
    turma_destino = relationship("ClassGroup")
    falta = relationship("Attendance")

    def __repr__(self) -> str:
        return f"<ClassMakeUp aluno_id={self.aluno_id} falta={self.data_falta} reposicao={self.data_reposicao}>"


class Evaluation(Base):
    """Avaliação pedagógica, conceito e relatório descritivo de portfólio."""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True)
    turma_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    professor_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    periodo = Column(String(50), nullable=False)  # ex: "1º Semestre 2026", "Módulo 1"
    data_avaliacao = Column(Date, nullable=False)
    conceito = Column(String(30), nullable=False, default=ConceitoAvaliacao.BOM.value)
    nota = Column(Float, nullable=True)  # Nota numérica opcional de 0 a 10
    relatorio_descritivo = Column(Text, nullable=False)  # Descrição da evolução técnica, traço, pintura
    criada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    aluno = relationship("Aluno")
    turma = relationship("ClassGroup")
    professor = relationship("Teacher")

    def __repr__(self) -> str:
        return f"<Evaluation aluno_id={self.aluno_id} periodo='{self.periodo}' conceito='{self.conceito}'>"
