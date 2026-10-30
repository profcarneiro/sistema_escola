from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    usuario_email = Column(String(150), nullable=True)
    acao = Column(String(50), nullable=False)
    entidade = Column(String(50), nullable=False)
    registro_id = Column(String(50), nullable=True)
    detalhes = Column(Text, nullable=True)
    ip = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    usuario = relationship("User", foreign_keys=[usuario_id])

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} acao='{self.acao}' entidade='{self.entidade}' usuario='{self.usuario_email}'>"
