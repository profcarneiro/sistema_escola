from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from app.models.attendance import StatusPresenca, StatusReposicao, ConceitoAvaliacao


def validar_janela_reposicao(data_falta: date, data_reposicao: date) -> None:
    """
    Regra do Briefing Helena Barufaldi:
    'Reposições feitas dentro do proprio mês ou na primeira semana do mês seguinte.'
    """
    if data_reposicao < data_falta:
        raise ValueError("A data de reposição não pode ser anterior à data da falta.")

    # Mesmo mês e ano
    if data_reposicao.year == data_falta.year and data_reposicao.month == data_falta.month:
        return

    # Mês seguinte
    ano_esperado = data_falta.year + 1 if data_falta.month == 12 else data_falta.year
    mes_esperado = 1 if data_falta.month == 12 else data_falta.month + 1

    if data_reposicao.year == ano_esperado and data_reposicao.month == mes_esperado:
        if data_reposicao.day <= 7:
            return
        raise ValueError(
            f"Reposição fora do prazo permitido! No mês seguinte à falta, a reposição deve ocorrer "
            f"impreterivelmente na primeira semana (até o dia 07/{mes_esperado:02d})."
        )

    raise ValueError(
        "Reposição fora do prazo permitido! Conforme as regras da Escola Helena Barufaldi, "
        "as reposições devem ser feitas dentro do próprio mês da falta ou até a primeira semana do mês seguinte."
    )


# ─── Diário de Classe (Lesson) ────────────────────────────────────────────────

class LessonBase(BaseModel):
    turma_id: int = Field(..., description="ID da turma")
    professor_id: int = Field(..., description="ID do professor")
    data_aula: date = Field(..., description="Data da aula")
    tema_aula: str = Field(..., min_length=2, max_length=200, description="Tema ou assunto da aula")
    conteudo_programatico: Optional[str] = Field(None, description="Técnicas, exercícios e conteúdos trabalhados")
    materiais_utilizados: Optional[str] = Field(None, max_length=255, description="Pincéis, tintas, papéis, etc.")
    observacoes: Optional[str] = Field(None, description="Observações pedagógicas gerais da aula")


class LessonCreate(LessonBase):
    pass


class LessonResponse(LessonBase):
    id: int
    criada_em: datetime
    turma_nome: Optional[str] = None
    professor_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Chamada e Frequência (Attendance) ────────────────────────────────────────

class AttendanceItem(BaseModel):
    aluno_id: int
    matricula_id: int
    status: StatusPresenca = StatusPresenca.PRESENTE
    motivo_justificativa: Optional[str] = Field(None, max_length=255)


class AttendanceBatchCreate(BaseModel):
    frequencias: List[AttendanceItem] = Field(..., min_length=1)


class AttendanceResponse(BaseModel):
    id: int
    lesson_id: int
    aluno_id: int
    matricula_id: int
    status: StatusPresenca
    motivo_justificativa: Optional[str] = None
    aluno_nome: Optional[str] = None
    criada_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Reposição de Aula (ClassMakeUp) ──────────────────────────────────────────

class ClassMakeUpCreate(BaseModel):
    aluno_id: int = Field(..., description="ID do aluno")
    matricula_origem_id: int = Field(..., description="ID da matrícula de origem")
    attendance_falta_id: Optional[int] = Field(None, description="ID do registro de falta correspondente")
    data_falta: date = Field(..., description="Data da falta que gerou a necessidade de reposição")
    turma_destino_id: int = Field(..., description="ID da turma em que a reposição será realizada")
    data_reposicao: date = Field(..., description="Data agendada para a reposição")
    observacoes: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validar_regra_de_prazo(self):
        validar_janela_reposicao(self.data_falta, self.data_reposicao)
        return self


class ClassMakeUpResponse(BaseModel):
    id: int
    aluno_id: int
    matricula_origem_id: int
    attendance_falta_id: Optional[int] = None
    data_falta: date
    turma_destino_id: int
    data_reposicao: date
    status: StatusReposicao
    observacoes: Optional[str] = None
    aluno_nome: Optional[str] = None
    turma_destino_nome: Optional[str] = None
    criada_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Avaliação Pedagógica e Portfólio ─────────────────────────────────────────

class EvaluationBase(BaseModel):
    aluno_id: int = Field(..., description="ID do aluno avaliado")
    turma_id: int = Field(..., description="ID da turma")
    professor_id: int = Field(..., description="ID do professor avaliador")
    periodo: str = Field(..., min_length=2, max_length=50, description="Período avaliativo, ex: 1º Semestre 2026")
    data_avaliacao: date = Field(..., description="Data da emissão da avaliação")
    conceito: ConceitoAvaliacao = Field(ConceitoAvaliacao.BOM, description="Conceito pedagógico global")
    nota: Optional[float] = Field(None, ge=0.0, le=10.0, description="Nota numérica opcional de 0 a 10")
    relatorio_descritivo: str = Field(
        ...,
        min_length=10,
        description="Relatório descritivo da evolução técnica, uso de materiais, criatividade e portfólio"
    )


class EvaluationCreate(EvaluationBase):
    pass


class EvaluationResponse(EvaluationBase):
    id: int
    criada_em: datetime
    aluno_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    professor_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
