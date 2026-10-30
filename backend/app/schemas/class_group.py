from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.class_group import FaixaEtaria, DiaSemana, Turno


HORARIO_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ClassGroupBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome da turma, ex: Aquarela Terça Tarde")
    curso_id: int = Field(..., description="ID da modalidade artística")
    sala_id: int = Field(..., description="ID da sala física de aula")
    professor_id: int = Field(..., description="ID do professor responsável")
    faixa_etaria: FaixaEtaria = Field(FaixaEtaria.ADULTO, description="Classificação etária da turma")
    dia_semana: DiaSemana = Field(..., description="Dia da semana da aula semanal")
    turno: Turno = Field(..., description="Turno da aula (MANHA, TARDE, NOITE)")
    horario_inicio: str = Field(..., description="Horário de início (HH:MM), ex: 09:00")
    horario_fim: str = Field(..., description="Horário de término (HH:MM), ex: 11:00")
    capacidade_maxima: int = Field(9, ge=1, le=9, description="Capacidade máxima da turma (teto de 9 alunos)")

    @field_validator("capacidade_maxima")
    @classmethod
    def validar_capacidade(cls, v: int) -> int:
        if v > 9:
            raise ValueError("A capacidade máxima de alunos por turma não pode exceder 9 (regra da escola).")
        if v < 1:
            raise ValueError("A capacidade deve ser de no mínimo 1 aluno.")
        return v

    @field_validator("horario_inicio", "horario_fim")
    @classmethod
    def validar_formato_hora(cls, v: str) -> str:
        v_clean = v.strip()
        if not HORARIO_REGEX.match(v_clean):
            raise ValueError(f"Horário '{v}' deve estar no formato 24h válido HH:MM (ex: '09:00', '14:30').")
        return v_clean

    @model_validator(mode="after")
    def validar_ordem_horarios(self):
        if self.horario_inicio and self.horario_fim:
            if self.horario_inicio >= self.horario_fim:
                raise ValueError("O horário de início deve ser anterior ao horário de término.")
        return self


class ClassGroupCreate(ClassGroupBase):
    pass


class ClassGroupUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    curso_id: Optional[int] = None
    sala_id: Optional[int] = None
    professor_id: Optional[int] = None
    faixa_etaria: Optional[FaixaEtaria] = None
    dia_semana: Optional[DiaSemana] = None
    turno: Optional[Turno] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    capacidade_maxima: Optional[int] = Field(None, ge=1, le=9)
    ativa: Optional[bool] = None

    @field_validator("capacidade_maxima")
    @classmethod
    def validar_capacidade(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v > 9:
                raise ValueError("A capacidade máxima de alunos por turma não pode exceder 9 (regra da escola).")
            if v < 1:
                raise ValueError("A capacidade deve ser de no mínimo 1 aluno.")
        return v

    @field_validator("horario_inicio", "horario_fim")
    @classmethod
    def validar_formato_hora(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not HORARIO_REGEX.match(v_clean):
                raise ValueError(f"Horário '{v}' deve estar no formato 24h válido HH:MM (ex: '09:00', '14:30').")
            return v_clean
        return v


class ClassGroupResponse(ClassGroupBase):
    id: int
    ativa: bool
    criada_em: datetime
    curso_nome: Optional[str] = None
    sala_nome: Optional[str] = None
    professor_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
