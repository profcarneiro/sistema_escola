from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.financial import Invoice
from app.models.enrollment import Matricula
from app.models.student import Aluno
from app.models.user import User, UserRole
from app.services.communication import (
    gerar_link_whatsapp,
    mensagem_lembrete_cobranca,
    mensagem_confirmacao_matricula
)
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/communication", tags=["Comunicação e WhatsApp"])


class WhatsAppLinkResponse(BaseModel):
    destinatario_nome: str
    telefone: str
    mensagem: str
    whatsapp_url: str


class CustomMessageRequest(BaseModel):
    telefone: str = Field(..., description="Telefone com DDD, ex: (19) 99999-9999")
    destinatario_nome: str = Field(..., description="Nome do destinatário")
    mensagem: str = Field(..., min_length=5, description="Texto da mensagem")


@router.post(
    "/whatsapp-invoice-reminder/{invoice_id}",
    response_model=WhatsAppLinkResponse,
    summary="Gerar link de WhatsApp para lembrete de cobrança"
)
def get_whatsapp_invoice_reminder(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value
    ))
):
    inv = db.query(Invoice).options(
        joinedload(Invoice.aluno).joinedload(Aluno.responsavel)
    ).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")

    # Prioriza o telefone do responsável financeiro se aluno for menor
    if inv.aluno.responsavel and inv.aluno.responsavel.telefone:
        dest_nome = inv.aluno.responsavel.nome
        telefone = inv.aluno.responsavel.telefone
    elif inv.aluno.telefone:
        dest_nome = inv.aluno.nome
        telefone = inv.aluno.telefone
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nem o aluno nem seu responsável possuem telefone cadastrado para WhatsApp."
        )

    msg = mensagem_lembrete_cobranca(
        nome_responsavel_ou_aluno=dest_nome,
        nome_aluno=inv.aluno.nome,
        descricao_titulo=inv.descricao,
        valor=inv.valor_final,
        data_vencimento=inv.data_vencimento
    )
    link = gerar_link_whatsapp(telefone, msg)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="WHATSAPP_COBRANCA_GERADO",
        entidade="Invoice",
        registro_id=str(inv.id),
        detalhes={"destinatario": dest_nome, "telefone": telefone},
        usuario=current_user,
        ip=client_ip
    )

    return WhatsAppLinkResponse(
        destinatario_nome=dest_nome,
        telefone=telefone,
        mensagem=msg,
        whatsapp_url=link
    )


@router.post(
    "/whatsapp-enrollment-welcome/{matricula_id}",
    response_model=WhatsAppLinkResponse,
    summary="Gerar link de WhatsApp para confirmação de matrícula"
)
def get_whatsapp_enrollment_welcome(
    matricula_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    mat = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma)
    ).filter(Matricula.id == matricula_id).first()
    if not mat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    telefone = (
        mat.aluno.responsavel.telefone if (mat.aluno.responsavel and mat.aluno.responsavel.telefone)
        else mat.aluno.telefone
    )
    if not telefone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum telefone cadastrado.")

    turma = mat.turma
    msg = mensagem_confirmacao_matricula(
        nome_aluno=mat.aluno.nome,
        modalidade=turma.nome if turma else "Arte",
        dia_semana=turma.dia_semana if turma else "Dia a definir",
        horario=f"{turma.horario_inicio} às {turma.horario_fim}" if turma else "",
        data_inicio=mat.data_inicio
    )
    link = gerar_link_whatsapp(telefone, msg)

    return WhatsAppLinkResponse(
        destinatario_nome=mat.aluno.nome,
        telefone=telefone,
        mensagem=msg,
        whatsapp_url=link
    )


@router.post(
    "/whatsapp-custom-link",
    response_model=WhatsAppLinkResponse,
    summary="Gerar link personalizado para WhatsApp"
)
def get_whatsapp_custom_link(
    msg_in: CustomMessageRequest,
    current_user: User = Depends(get_current_active_user)
):
    link = gerar_link_whatsapp(msg_in.telefone, msg_in.mensagem)
    return WhatsAppLinkResponse(
        destinatario_nome=msg_in.destinatario_nome,
        telefone=msg_in.telefone,
        mensagem=msg_in.mensagem,
        whatsapp_url=link
    )
