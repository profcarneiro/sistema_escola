from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class RoomBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=50, description="Nome identificador da sala (ex: Sala 1)")
    capacidade: int = Field(9, ge=1, description="Capacidade máxima de alunos permitidos na sala")
    descricao: Optional[str] = Field(None, max_length=255, description="Descrição ou recursos da sala")

    @field_validator("capacidade")
    @classmethod
    def validar_capacidade_maxima(cls, v: int) -> int:
        if v < 1:
            raise ValueError("A capacidade mínima da sala deve ser de pelo menos 1 aluno.")
        return v


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=50)
    capacidade: Optional[int] = Field(None, ge=1)
    descricao: Optional[str] = Field(None, max_length=255)
    ativa: Optional[bool] = None

    @field_validator("capacidade")
    @classmethod
    def validar_capacidade_maxima(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("A capacidade mínima da sala deve ser de pelo menos 1 aluno.")
        return v


class RoomResponse(RoomBase):
    id: int
    ativa: bool
    criada_em: datetime

    model_config = ConfigDict(from_attributes=True)
