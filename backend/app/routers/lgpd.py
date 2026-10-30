from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.lgpd import LGPDConsent, TermoTipo
from app.models.user import User, UserRole
from app.schemas.lgpd import (
    LGPDConsentCreate,
    LGPDConsentResponse,
    LGPDConsentRevogar,
    TermoTipoEnum,
)
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/lgpd", tags=["LGPD e Consentimentos"])


@router.post(
    "/consentimentos",
    response_model=LGPDConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar termo de consentimento LGPD"
)
def registrar_consentimento(
    consent_in: LGPDConsentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Registra formalmente o consentimento LGPD para um titular (aluno, responsável, professor).
    Valida obrigatoriedade de responsável legal quando o titular for menor de idade.
    """
    client_ip = request.client.host if request.client else None

    # Validação adicional defensiva de menor de idade
    if consent_in.menor_idade and (not consent_in.responsavel_nome or not consent_in.responsavel_nome.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Para titulares menores de idade, o nome do responsável legal é estritamente obrigatório."
        )

    novo_consentimento = LGPDConsent(
        titular_nome=consent_in.titular_nome.strip(),
        titular_tipo=consent_in.titular_tipo.strip().upper(),
        responsavel_nome=consent_in.responsavel_nome.strip() if consent_in.responsavel_nome else None,
        menor_idade=consent_in.menor_idade,
        termo_tipo=consent_in.termo_tipo.value,
        consentido=consent_in.consentido,
        versao_termo=consent_in.versao_termo,
        observacoes=consent_in.observacoes,
        ip=client_ip
    )
    db.add(novo_consentimento)
    db.commit()
    db.refresh(novo_consentimento)

    registrar_auditoria(
        db=db,
        acao="LGPD_CONSENTIMENTO_REGISTRADO",
        entidade="LGPDConsent",
        registro_id=str(novo_consentimento.id),
        detalhes={
            "titular_nome": novo_consentimento.titular_nome,
            "termo_tipo": novo_consentimento.termo_tipo,
            "menor_idade": novo_consentimento.menor_idade,
            "responsavel_nome": novo_consentimento.responsavel_nome,
            "consentido": novo_consentimento.consentido,
            "versao_termo": novo_consentimento.versao_termo
        },
        usuario=current_user,
        ip=client_ip
    )

    return novo_consentimento


@router.get(
    "/consentimentos",
    response_model=List[LGPDConsentResponse],
    summary="Listar registros de consentimento"
)
def listar_consentimentos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    titular: Optional[str] = Query(None, description="Filtrar por nome do titular"),
    termo_tipo: Optional[TermoTipoEnum] = Query(None, description="Filtrar por tipo de termo"),
    menor_idade: Optional[bool] = Query(None, description="Filtrar por menor de idade"),
    apenas_consentidos: Optional[bool] = Query(None, description="Filtrar apenas consentimentos válidos/ativos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    """Consulta os termos de consentimento registrados com suporte a filtros detalhados (Acesso restrito à Direção, Coordenação e Secretaria)."""
    query = db.query(LGPDConsent)

    if titular:
        query = query.filter(LGPDConsent.titular_nome.ilike(f"%{titular.strip()}%"))
    if termo_tipo:
        query = query.filter(LGPDConsent.termo_tipo == termo_tipo.value)
    if menor_idade is not None:
        query = query.filter(LGPDConsent.menor_idade == menor_idade)
    if apenas_consentidos is not None:
        query = query.filter(LGPDConsent.consentido == apenas_consentidos)

    registros = query.order_by(LGPDConsent.timestamp.desc()).offset(skip).limit(limit).all()
    return registros


@router.get(
    "/consentimentos/{consentimento_id}",
    response_model=LGPDConsentResponse,
    summary="Obter detalhes de um consentimento por ID"
)
def obter_consentimento(
    consentimento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    """Retorna os dados completos de um registro de consentimento."""
    consent = db.query(LGPDConsent).filter(LGPDConsent.id == consentimento_id).first()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de consentimento não encontrado."
        )
    return consent


@router.post(
    "/consentimentos/{consentimento_id}/revogar",
    response_model=LGPDConsentResponse,
    summary="Revogar termo de consentimento (Direito ao Esquecimento / Revogação LGPD)"
)
def revogar_consentimento(
    consentimento_id: int,
    dados_revogacao: LGPDConsentRevogar,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    """Revoga formalmente um consentimento previamente concedido, registrando a solicitação para fins de auditoria."""
    client_ip = request.client.host if request.client else None
    consent = db.query(LGPDConsent).filter(LGPDConsent.id == consentimento_id).first()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de consentimento não encontrado."
        )

    consent.consentido = False
    if dados_revogacao.motivo:
        obs_atual = consent.observacoes or ""
        consent.observacoes = f"{obs_atual} | REVOGADO: {dados_revogacao.motivo.strip()}".strip(" |")

    db.commit()
    db.refresh(consent)

    registrar_auditoria(
        db=db,
        acao="LGPD_CONSENTIMENTO_REVOGADO",
        entidade="LGPDConsent",
        registro_id=str(consent.id),
        detalhes={
            "titular_nome": consent.titular_nome,
            "termo_tipo": consent.termo_tipo,
            "motivo_revogacao": dados_revogacao.motivo
        },
        usuario=current_user,
        ip=client_ip
    )

    return consent
