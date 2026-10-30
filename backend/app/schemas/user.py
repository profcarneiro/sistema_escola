from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRoleEnum(str, Enum):
    DIRECAO = "Direção"
    COORDENACAO = "Coordenação"
    SECRETARIA = "Secretaria"
    FINANCEIRO = "Financeiro"
    PROFESSOR = "Professor"


class UserBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="E-mail de acesso único")
    role: UserRoleEnum = Field(default=UserRoleEnum.SECRETARIA, description="Perfil de acesso (RBAC)")
    ativo: bool = Field(default=True, description="Indica se a conta está ativa")


class UserCreate(UserBase):
    senha: str = Field(..., min_length=6, max_length=100, description="Senha de acesso (mínimo 6 caracteres)")


class UserUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[UserRoleEnum] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = Field(None, min_length=6, max_length=100)


class UserResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    role: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="E-mail cadastrado")
    senha: str = Field(..., description="Senha de acesso")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
