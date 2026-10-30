from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class TermoTipoEnum(str, Enum):
    GERAL = "GERAL"
    IMAGEM = "IMAGEM"
    SAUDE = "SAUDE"


class LGPDConsentBase(BaseModel):
    titular_nome: str = Field(..., min_length=2, max_length=150, description="Nome do titular dos dados")
    titular_tipo: str = Field(default="ALUNO", description="Tipo do titular: ALUNO, RESPONSAVEL, PROFESSOR")
    responsavel_nome: Optional[str] = Field(None, max_length=150, description="Nome do responsável legal (obrigatório para menores)")
    menor_idade: bool = Field(default=False, description="Indica se o titular é menor de idade")
    termo_tipo: TermoTipoEnum = Field(..., description="Tipo do termo: GERAL, IMAGEM ou SAUDE")
    consentido: bool = Field(default=True, description="Indica se o consentimento foi concedido (True) ou revogado (False)")
    versao_termo: str = Field(default="1.0", description="Versão do termo aceito")
    observacoes: Optional[str] = Field(None, description="Observações complementares")


class LGPDConsentCreate(LGPDConsentBase):
    @model_validator(mode="after")
    def validar_responsavel_menor(self) -> "LGPDConsentCreate":
        if self.menor_idade:
            if not self.responsavel_nome or not self.responsavel_nome.strip():
                raise ValueError("Para menores de idade, o nome do responsável legal é obrigatório.")
        return self


class LGPDConsentResponse(LGPDConsentBase):
    id: int
    timestamp: datetime
    ip: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LGPDConsentRevogar(BaseModel):
    motivo: Optional[str] = Field(None, description="Motivo da revogação do consentimento")
