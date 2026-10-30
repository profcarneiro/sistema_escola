from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class TeacherBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do professor")
    email: EmailStr = Field(..., description="E-mail profissional para contato")
    telefone: Optional[str] = Field(None, max_length=30, description="Telefone de contato, ex: (19) 99999-9999")
    endereco: Optional[str] = Field(None, max_length=255, description="Endereço residencial")
    especialidades: Optional[str] = Field(None, description="Modalidades que o professor leciona")
    disponibilidade: Optional[str] = Field(None, description="Horários e dias disponíveis")
    substituto_id: Optional[int] = Field(None, description="ID do professor substituto preferencial")
    user_id: Optional[int] = Field(None, description="ID do usuário de acesso ao sistema (se houver)")


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=30)
    endereco: Optional[str] = Field(None, max_length=255)
    especialidades: Optional[str] = None
    disponibilidade: Optional[str] = None
    substituto_id: Optional[int] = None
    user_id: Optional[int] = None
    ativo: Optional[bool] = None


class TeacherResponse(TeacherBase):
    id: int
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
