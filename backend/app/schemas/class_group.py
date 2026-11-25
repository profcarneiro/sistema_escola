from datetime import datetime
import re
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.class_group import FaixaEtaria, DiaSemana, Turno


HORARIO_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class CourseResumo(BaseModel):
    id: int
    nome: str
    valor_mensalidade: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ClassGroupBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome da turma, ex: Aquarela Terça Tarde")
    curso_id: Optional[int] = Field(None, description="ID da modalidade artística principal (compatibilidade)")
    cursos_ids: List[int] = Field(default_factory=list, description="IDs das modalidades artísticas da turma (turmas mistas)")
    sala_id: int = Field(..., description="ID da sala física de aula")
    professor_id: int = Field(..., description="ID do professor responsável")
    faixa_etaria: Optional[FaixaEtaria] = Field(None, description="Classificação etária da turma")
    dia_semana: DiaSemana = Field(..., description="Dia da semana da aula semanal")
    turno: Turno = Field(..., description="Turno da aula (MANHA, TARDE, NOITE)")
    horario_inicio: str = Field(..., description="Horário de início (HH:MM), ex: 09:00")
    horario_fim: str = Field(..., description="Horário de término (HH:MM), ex: 11:00")
    capacidade_maxima: Optional[int] = Field(None, ge=1, description="Capacidade máxima da turma (até a capacidade da sala)")

    @field_validator("capacidade_maxima")
    @classmethod
    def validar_capacidade(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
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
    faixa_etaria: FaixaEtaria = Field(..., description="Classificação etária da turma (seleção obrigatória)")

    @model_validator(mode="after")
    def validar_cursos_informados(self):
        ids: List[int] = []
        for cid in self.cursos_ids or []:
            if cid not in ids:
                ids.append(cid)
        if not ids and self.curso_id is not None:
            ids.append(self.curso_id)
        if not ids:
            raise ValueError("Selecione pelo menos um curso/modalidade para a turma.")
        self.cursos_ids = ids
        self.curso_id = ids[0]
        return self


class ClassGroupUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    curso_id: Optional[int] = None
    cursos_ids: Optional[List[int]] = None
    sala_id: Optional[int] = None
    professor_id: Optional[int] = None
    faixa_etaria: Optional[FaixaEtaria] = None
    dia_semana: Optional[DiaSemana] = None
    turno: Optional[Turno] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    capacidade_maxima: Optional[int] = Field(None, ge=1)
    ativa: Optional[bool] = None

    @field_validator("capacidade_maxima")
    @classmethod
    def validar_capacidade(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("A capacidade deve ser de no mínimo 1 aluno.")
        return v

    @field_validator("cursos_ids")
    @classmethod
    def validar_cursos_ids(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            ids: List[int] = []
            for cid in v:
                if cid not in ids:
                    ids.append(cid)
            if not ids:
                raise ValueError("A turma deve possuir pelo menos um curso/modalidade associado.")
            return ids
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
    capacidade_maxima: int
    ativa: bool
    criada_em: datetime
    curso_nome: Optional[str] = None
    cursos_ids: List[int] = Field(default_factory=list)
    cursos_nomes: List[str] = Field(default_factory=list)
    cursos: List[CourseResumo] = Field(default_factory=list)
    sala_nome: Optional[str] = None
    professor_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
