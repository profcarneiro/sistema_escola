from datetime import date, datetime
from typing import Optional
import re
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


CPF_REGEX = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")


class ResponsavelBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do responsável legal")
    cpf: str = Field(..., description="CPF do responsável (formato: 000.000.000-00)")
    telefone: str = Field(..., max_length=30, description="Telefone com DDD, ex: (19) 99999-9999")
    email: str = Field(..., description="E-mail do responsável para comunicação")
    endereco: str = Field(..., max_length=255, description="Endereço residencial completo")

    @field_validator("cpf")
    @classmethod
    def validar_formato_cpf(cls, v: str) -> str:
        v_clean = v.strip()
        if not CPF_REGEX.match(v_clean):
            raise ValueError("CPF deve estar no formato 000.000.000-00.")
        return v_clean


class ResponsavelCreate(ResponsavelBase):
    pass


class ResponsavelUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    cpf: Optional[str] = None
    telefone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = None
    endereco: Optional[str] = Field(None, max_length=255)

    @field_validator("cpf")
    @classmethod
    def validar_formato_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not CPF_REGEX.match(v.strip()):
                raise ValueError("CPF deve estar no formato 000.000.000-00.")
            return v.strip()
        return v


class ResponsavelResponse(ResponsavelBase):
    id: int
    aluno_id: int
    responsavel_financeiro: bool
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
