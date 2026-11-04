from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.enrollment import StatusMatricula

TIPOS_DESCONTO = ["irmao", "indicacao", "bolsa"]


class MatriculaBase(BaseModel):
    aluno_id: int = Field(..., description="ID do aluno a ser matriculado")
    turma_id: int = Field(..., description="ID da turma de destino")
    data_matricula: date = Field(..., description="Data da formalização da matrícula")
    data_inicio: date = Field(..., description="Data de início das aulas")
    data_termino_previsto: Optional[date] = Field(None, description="Data prevista de término do curso")
    valor_mensalidade: float = Field(..., ge=0.0, description="Valor base da mensalidade em R$")
    desconto_percentual: float = Field(0.0, ge=0.0, le=100.0, description="Desconto aplicado em %")
    tipo_desconto: Optional[str] = Field(None, description="Tipo de desconto: irmao, indicacao, bolsa")
    dia_vencimento: Optional[int] = Field(10, ge=1, le=31, description="Dia preferencial de vencimento das parcelas")
    quantidade_parcelas: Optional[int] = Field(12, ge=1, le=24, description="Quantidade de mensalidades/parcelas contratadas")
    aula_experimental: bool = Field(False, description="Indica se é uma matrícula experimental/cortesia")
    observacoes: Optional[str] = Field(None, description="Observações gerais da matrícula")

    @field_validator("tipo_desconto")
    @classmethod
    def validar_tipo_desconto(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in TIPOS_DESCONTO:
            raise ValueError(f"Tipo de desconto inválido. Valores aceitos: {', '.join(TIPOS_DESCONTO)}.")
        return v.lower() if v else None


class MatriculaCreate(MatriculaBase):
    pass


class MatriculaUpdate(BaseModel):
    status: Optional[StatusMatricula] = None
    contrato_assinado: Optional[bool] = None
    data_assinatura_contrato: Optional[datetime] = None
    valor_mensalidade: Optional[float] = Field(None, ge=0.0)
    desconto_percentual: Optional[float] = Field(None, ge=0.0, le=100.0)
    tipo_desconto: Optional[str] = None
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    quantidade_parcelas: Optional[int] = Field(None, ge=1, le=24)
    motivo_cancelamento: Optional[str] = None
    multa_cancelamento: Optional[float] = Field(None, ge=0.0)
    observacoes: Optional[str] = None

    @field_validator("tipo_desconto")
    @classmethod
    def validar_tipo_desconto(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in TIPOS_DESCONTO:
            raise ValueError(f"Tipo de desconto inválido. Valores aceitos: {', '.join(TIPOS_DESCONTO)}.")
        return v.lower() if v else None


class MatriculaResponse(MatriculaBase):
    id: int
    status: StatusMatricula
    numero_contrato: Optional[str] = None
    contrato_assinado: bool
    data_assinatura_contrato: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None
    data_cancelamento: Optional[datetime] = None
    multa_cancelamento: float
    aluno_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    valor_com_desconto: Optional[float] = None
    dia_vencimento: Optional[int] = 10
    quantidade_parcelas: Optional[int] = 12
    criada_em: datetime

    model_config = ConfigDict(from_attributes=True)


class ListaEsperaCreate(BaseModel):
    aluno_id: int = Field(..., description="ID do aluno para a lista de espera")
    turma_id: int = Field(..., description="ID da turma desejada")
    observacoes: Optional[str] = Field(None, max_length=255)


class ListaEsperaResponse(ListaEsperaCreate):
    id: int
    posicao: int
    ativa: bool
    notificado: bool
    data_entrada: datetime
    aluno_nome: Optional[str] = None
    turma_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
