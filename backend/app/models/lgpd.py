from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from app.database import Base


class TermoTipo(str, enum.Enum):
    GERAL = "GERAL"
    IMAGEM = "IMAGEM"
    SAUDE = "SAUDE"


class LGPDConsent(Base):
    __tablename__ = "lgpd_consents"

    id = Column(Integer, primary_key=True, index=True)
    titular_nome = Column(String(150), nullable=False, index=True)
    titular_tipo = Column(String(50), nullable=False, default="ALUNO")  # ALUNO, RESPONSAVEL, PROFESSOR
    responsavel_nome = Column(String(150), nullable=True)
    menor_idade = Column(Boolean, default=False, nullable=False)
    termo_tipo = Column(String(50), nullable=False)  # GERAL, IMAGEM, SAUDE
    consentido = Column(Boolean, default=True, nullable=False)
    versao_termo = Column(String(20), default="1.0", nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip = Column(String(50), nullable=True)
    observacoes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<LGPDConsent id={self.id} titular='{self.titular_nome}' termo='{self.termo_tipo}' consentido={self.consentido}>"
