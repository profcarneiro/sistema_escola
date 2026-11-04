from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from app.database import Base


class UserRole(str, enum.Enum):
    DIRECAO = "Direção"
    COORDENACAO = "Coordenação"
    SECRETARIA = "Secretaria"
    FINANCEIRO = "Financeiro"
    PROFESSOR = "Professor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.SECRETARIA.value)
    professor_id = Column(Integer, ForeignKey("teachers.id", use_alter=True, name="fk_users_professor_id", ondelete="SET NULL"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizado_em = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} nome='{self.nome}' email='{self.email}' role='{self.role}'>"
