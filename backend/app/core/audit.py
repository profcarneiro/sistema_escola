import json
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def registrar_auditoria(
    db: Session,
    acao: str,
    entidade: str,
    registro_id: Optional[str] = None,
    detalhes: Optional[Any] = None,
    usuario: Optional[User] = None,
    usuario_email: Optional[str] = None,
    ip: Optional[str] = None,
) -> AuditLog:
    """Registra uma entrada no log de auditoria do sistema."""
    detalhes_str = None
    if detalhes is not None:
        if isinstance(detalhes, (dict, list)):
            # Remove campos sensíveis se existirem
            if isinstance(detalhes, dict):
                copia = {
                    k: ("[OCULTO]" if any(s in k.lower() for s in ["senha", "password", "token", "secret"]) else v)
                    for k, v in detalhes.items()
                }
                detalhes_str = json.dumps(copia, ensure_ascii=False)
            else:
                detalhes_str = json.dumps(detalhes, ensure_ascii=False)
        else:
            detalhes_str = str(detalhes)

    email_final = usuario_email
    usuario_id = None
    if usuario is not None:
        usuario_id = usuario.id
        email_final = email_final or usuario.email

    audit_entry = AuditLog(
        usuario_id=usuario_id,
        usuario_email=email_final,
        acao=acao,
        entidade=entidade,
        registro_id=str(registro_id) if registro_id is not None else None,
        detalhes=detalhes_str,
        ip=ip,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
