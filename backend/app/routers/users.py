from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.routers.auth import require_roles

router = APIRouter(
    prefix="/users",
    tags=["Usuários"],
    dependencies=[Depends(require_roles(UserRole.DIRECAO.value))]
)


@router.get("/", response_model=List[UserResponse], summary="Listar usuários (Apenas Direção)")
def list_users(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros retornados"),
    role: Optional[str] = Query(None, description="Filtrar por perfil"),
    busca: Optional[str] = Query(None, description="Busca por nome ou e-mail"),
    db: Session = Depends(get_db)
):
    """Lista todos os colaboradores e seus perfis com suporte a filtros e paginação."""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter((User.nome.ilike(termo)) | (User.email.ilike(termo)))

    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo usuário (Apenas Direção)")
def create_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    """Cadastra um novo usuário colaborador no sistema com senha criptografada."""
    client_ip = request.client.host if request.client else None
    email_clean = user_in.email.strip().lower()

    # Verifica duplicidade de e-mail
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este e-mail."
        )

    novo_usuario = User(
        nome=user_in.nome.strip(),
        email=email_clean,
        senha_hash=get_password_hash(user_in.senha),
        role=user_in.role.value,
        ativo=user_in.ativo
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    registrar_auditoria(
        db=db,
        acao="USUARIO_CRIADO",
        entidade="User",
        registro_id=str(novo_usuario.id),
        detalhes={"nome": novo_usuario.nome, "email": novo_usuario.email, "role": novo_usuario.role},
        usuario=current_user,
        ip=client_ip
    )

    return novo_usuario


@router.get("/{user_id}", response_model=UserResponse, summary="Obter detalhes do usuário por ID")
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Retorna os dados cadastrais do usuário solicitado."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar dados do usuário")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    """Atualiza dados cadastrais, cargo, status ou senha de um usuário."""
    client_ip = request.client.host if request.client else None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )

    alteracoes = {}

    if user_update.nome is not None:
        user.nome = user_update.nome.strip()
        alteracoes["nome"] = user.nome

    if user_update.email is not None:
        email_clean = user_update.email.strip().lower()
        if email_clean != user.email:
            existing = db.query(User).filter(User.email == email_clean).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já está em uso por outro usuário."
                )
            user.email = email_clean
            alteracoes["email"] = user.email

    if user_update.role is not None:
        user.role = user_update.role.value
        alteracoes["role"] = user.role

    if user_update.ativo is not None:
        user.ativo = user_update.ativo
        alteracoes["ativo"] = user.ativo

    if user_update.senha is not None and user_update.senha.strip():
        user.senha_hash = get_password_hash(user_update.senha)
        alteracoes["senha_atualizada"] = True

    db.commit()
    db.refresh(user)

    registrar_auditoria(
        db=db,
        acao="USUARIO_ATUALIZADO",
        entidade="User",
        registro_id=str(user.id),
        detalhes=alteracoes,
        usuario=current_user,
        ip=client_ip
    )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Excluir usuário")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    """Remove um colaborador do sistema. Não permite auto-exclusão do usuário logado."""
    client_ip = request.client.host if request.client else None

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido excluir o próprio usuário logado."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )

    dados_excluidos = {"id": user.id, "nome": user.nome, "email": user.email, "role": user.role}
    db.delete(user)
    db.commit()

    registrar_auditoria(
        db=db,
        acao="USUARIO_EXCLUIDO",
        entidade="User",
        registro_id=str(user_id),
        detalhes=dados_excluidos,
        usuario=current_user,
        ip=client_ip
    )

    return {"mensagem": f"Usuário {dados_excluidos['nome']} excluído com sucesso."}
