from datetime import datetime
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserRoleEnum(str, Enum):
    DIRECAO = "Direção"
    COORDENACAO = "Coordenação"
    SECRETARIA = "Secretaria"
    FINANCEIRO = "Financeiro"
    PROFESSOR = "Professor"


ROLE_MAP: Dict[str, UserRoleEnum] = {
    "direcao": UserRoleEnum.DIRECAO,
    "direção": UserRoleEnum.DIRECAO,
    "admin": UserRoleEnum.DIRECAO,
    "administrador": UserRoleEnum.DIRECAO,
    "coordenacao": UserRoleEnum.COORDENACAO,
    "coordenação": UserRoleEnum.COORDENACAO,
    "secretaria": UserRoleEnum.SECRETARIA,
    "recepcao": UserRoleEnum.SECRETARIA,
    "recepção": UserRoleEnum.SECRETARIA,
    "atendimento": UserRoleEnum.SECRETARIA,
    "financeiro": UserRoleEnum.FINANCEIRO,
    "professor": UserRoleEnum.PROFESSOR,
    "docente": UserRoleEnum.PROFESSOR,
}


class UserBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="E-mail de acesso único")
    role: UserRoleEnum = Field(default=UserRoleEnum.SECRETARIA, description="Perfil de acesso (RBAC)")
    professor_id: Optional[int] = Field(None, description="ID do professor vinculado caso perfil seja Professor")
    ativo: bool = Field(default=True, description="Indica se a conta está ativa")

    @field_validator("role", mode="before")
    @classmethod
    def normalizar_role(cls, v):
        if isinstance(v, UserRoleEnum):
            return v
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ROLE_MAP:
                return ROLE_MAP[v_clean]
        return v


class UserCreate(UserBase):
    senha: str = Field(..., min_length=6, max_length=100, description="Senha de acesso (mínimo 6 caracteres)")


class UserUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[UserRoleEnum] = None
    professor_id: Optional[int] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = Field(None, min_length=6, max_length=100)

    @field_validator("role", mode="before")
    @classmethod
    def normalizar_role_update(cls, v):
        if v is None:
            return v
        if isinstance(v, UserRoleEnum):
            return v
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ROLE_MAP:
                return ROLE_MAP[v_clean]
        return v


class UserResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    role: str
    professor_id: Optional[int] = None
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
