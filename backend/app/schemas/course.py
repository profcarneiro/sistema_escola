from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CourseBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome da modalidade artística")
    descricao: Optional[str] = Field(None, description="Ementa e detalhes do curso")
    duracao_meses: Optional[int] = Field(12, ge=1, le=48, description="Duração estimada em meses")
    valor_mensalidade: float = Field(250.0, ge=0.0, description="Valor base da mensalidade em R$")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    descricao: Optional[str] = None
    duracao_meses: Optional[int] = Field(None, ge=1, le=48)
    valor_mensalidade: Optional[float] = Field(None, ge=0.0)
    ativo: Optional[bool] = None


class CourseResponse(CourseBase):
    id: int
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
