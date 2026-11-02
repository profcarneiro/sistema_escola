from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.schemas.guardian import ResponsavelCreate, ResponsavelResponse


def calcular_idade(data_nascimento: date) -> int:
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )


class AlunoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do aluno")
    data_nascimento: date = Field(..., description="Data de nascimento (formato DD/MM/AAAA ao inserir)")
    cpf: Optional[str] = Field(None, description="CPF (apenas para alunos maiores de idade)")
    email: Optional[str] = Field(None, description="E-mail do aluno (opcional para menores)")
    telefone: Optional[str] = Field(None, max_length=30, description="Telefone do aluno")
    endereco: Optional[str] = Field(None, max_length=255, description="Endereço do aluno")
    alergias: Optional[str] = Field(None, description="Alergias conhecidas do aluno")
    medicacoes: Optional[str] = Field(None, description="Medicações em uso")
    observacoes_saude: Optional[str] = Field(None, description="Observações gerais de saúde")
    autorizacao_imagem: bool = Field(False, description="Autorização de uso de imagem")


class AlunoCreate(AlunoBase):
    """
    Criação de aluno. Para menores de idade (< 18 anos),
    o campo 'responsavel' é OBRIGATÓRIO (regra explícita do briefing).
    """
    responsavel: Optional[ResponsavelCreate] = Field(
        None,
        description="Responsável legal/financeiro. OBRIGATÓRIO para alunos menores de 18 anos."
    )

    @model_validator(mode="after")
    def validar_responsavel_para_menor(self):
        idade = calcular_idade(self.data_nascimento)
        if idade < 18 and self.responsavel is None:
            raise ValueError(
                "Para alunos menores de 18 anos, o cadastro do responsável legal e financeiro é obrigatório."
            )
        return self


class AlunoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[str] = None
    telefone: Optional[str] = Field(None, max_length=30)
    endereco: Optional[str] = Field(None, max_length=255)
    alergias: Optional[str] = None
    medicacoes: Optional[str] = None
    observacoes_saude: Optional[str] = None
    autorizacao_imagem: Optional[bool] = None
    ativo: Optional[bool] = None


class AlunoResponse(AlunoBase):
    id: int
    ativo: bool
    criado_em: datetime
    responsavel: Optional[ResponsavelResponse] = None

    @property
    def menor_de_idade(self) -> bool:
        return calcular_idade(self.data_nascimento) < 18

    model_config = ConfigDict(from_attributes=True)
