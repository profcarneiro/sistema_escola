from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.enrollment import StatusMatricula, TipoCortesia
from app.models.discount_policy import CondicaoPagamento

TIPOS_DESCONTO = ["irmao", "indicacao", "bolsa", "plano", "combinado", "manual"]


class MatriculaBase(BaseModel):
    aluno_id: int = Field(..., description="ID do aluno a ser matriculado")
    turma_id: int = Field(..., description="ID da turma de destino")
    curso_id: Optional[int] = Field(None, description="ID do curso específico do aluno na turma (para turmas mistas)")
    data_matricula: date = Field(..., description="Data da formalização da matrícula")
    data_inicio: date = Field(..., description="Data de início das aulas")
    data_termino_previsto: Optional[date] = Field(None, description="Data prevista de término do contrato")
    data_saida: Optional[date] = Field(None, description="Data efetiva de saída/cancelamento/fim do contrato")

    valor_mensalidade: float = Field(..., ge=0.0, description="Valor mensal base do curso em R$")
    duracao_contrato_meses: Optional[int] = Field(None, ge=1, le=48, description="Duração do contrato em meses/aulas")
    condicao_pagamento: CondicaoPagamento = Field(CondicaoPagamento.MENSAL, description="Condição: A_VISTA, PARCELADO ou MENSAL")
    plano_id: Optional[int] = Field(None, description="ID do plano da política de descontos selecionado")

    desconto_percentual: Optional[float] = Field(None, ge=0.0, le=100.0, description="Desconto aplicado em %")
    desconto_valor_fixo: float = Field(0.0, ge=0.0, description="Desconto adicional em R$")
    descontos_ids: List[int] = Field(default_factory=list, description="IDs de descontos adicionais acumulados (ex: irmão + indicação)")
    tipo_desconto: Optional[str] = Field(None, description="Tipo de desconto: irmao, indicacao, bolsa, plano, combinado, manual")
    desconto_editado_manualmente: Optional[bool] = Field(None, description="Sinaliza se o desconto foi alterado manualmente")
    desconto_motivo_alteracao: Optional[str] = Field(None, description="Motivo da alteração manual de desconto")

    dia_vencimento: Optional[int] = Field(10, ge=1, le=31, description="Dia preferencial de vencimento das parcelas")
    quantidade_parcelas: Optional[int] = Field(12, ge=1, le=48, description="Quantidade de cobranças/parcelas")

    aula_experimental: bool = Field(False, description="Indica se é uma matrícula experimental/cortesia")
    is_cortesia: bool = Field(False, description="Indica se é matrícula cortesia/sem cobrança (quitado, bolsa 100%, reposição)")
    tipo_cortesia: Optional[TipoCortesia] = Field(None, description="Motivo da cortesia: CONTRATO_QUITADO, BOLSA_100, REPOSICAO")
    observacoes: Optional[str] = Field(None, description="Observações gerais da matrícula")

    @field_validator("tipo_desconto")
    @classmethod
    def validar_tipo_desconto(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in TIPOS_DESCONTO:
            raise ValueError(f"Tipo de desconto inválido. Valores aceitos: {', '.join(TIPOS_DESCONTO)}.")
        return v.lower() if v else None

    @model_validator(mode="after")
    def validar_condicao_e_cortesia(self):
        if self.condicao_pagamento == CondicaoPagamento.PARCELADO and self.quantidade_parcelas is not None:
            if self.quantidade_parcelas < 1 or self.quantidade_parcelas > 12:
                raise ValueError("Na condição PARCELADO, a quantidade de parcelas deve ser de 1x a 12x.")
        if self.is_cortesia and self.tipo_cortesia is None:
            raise ValueError("Informe o tipo de cortesia: CONTRATO_QUITADO, BOLSA_100 ou REPOSICAO.")
        return self


class MatriculaCreate(MatriculaBase):
    pass


class MatriculaUpdate(BaseModel):
    status: Optional[StatusMatricula] = None
    curso_id: Optional[int] = None
    data_termino_previsto: Optional[date] = None
    data_saida: Optional[date] = None
    contrato_assinado: Optional[bool] = None
    data_assinatura_contrato: Optional[datetime] = None

    valor_mensalidade: Optional[float] = Field(None, ge=0.0)
    duracao_contrato_meses: Optional[int] = Field(None, ge=1, le=48)
    condicao_pagamento: Optional[CondicaoPagamento] = None
    plano_id: Optional[int] = None

    desconto_percentual: Optional[float] = Field(None, ge=0.0, le=100.0)
    desconto_valor_fixo: Optional[float] = Field(None, ge=0.0)
    descontos_ids: Optional[List[int]] = None
    tipo_desconto: Optional[str] = None
    desconto_editado_manualmente: Optional[bool] = None
    desconto_motivo_alteracao: Optional[str] = None

    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    quantidade_parcelas: Optional[int] = Field(None, ge=1, le=48)
    aula_experimental: Optional[bool] = None
    is_cortesia: Optional[bool] = None
    tipo_cortesia: Optional[TipoCortesia] = None
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
    duracao_contrato_meses: int = 12
    valor_total_contrato: Optional[float] = None
    plano_nome: Optional[str] = None
    desconto_percentual: float = 0.0
    desconto_valor_fixo: float = 0.0
    desconto_plano_percentual: float = 0.0
    desconto_adicional_percentual: float = 0.0
    desconto_editado_manualmente: bool = False
    desconto_alterado_por_nome: Optional[str] = None
    desconto_alterado_em: Optional[datetime] = None
    descontos_aplicados: List[Any] = Field(default_factory=list)
    motivo_cancelamento: Optional[str] = None
    data_cancelamento: Optional[datetime] = None
    multa_cancelamento: float
    aluno_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    curso_nome: Optional[str] = None
    valor_com_desconto: Optional[float] = None
    dia_vencimento: Optional[int] = 10
    quantidade_parcelas: Optional[int] = 12
    total_parcelas_geradas: int = 0
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
