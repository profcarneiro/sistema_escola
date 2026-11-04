from typing import Optional, List, Callable
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_access_token, decode_access_token
from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.user import User, UserRole
from app.models.teacher import Teacher
from app.schemas.user import UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Esquema OAuth2 configurado apontando para login-form
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login-form",
    auto_error=False
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Valida o token JWT e retorna a instância do usuário autenticado."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais do token incompletas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado ao token não foi encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Garante que o usuário autenticado esteja com status ativo."""
    if not current_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo no sistema. Contate a Direção."
        )
    return current_user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Factory de dependência para controle de acesso baseado em perfis (RBAC)."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Se nenhuma role for especificada ou se a role do usuário estiver na lista permitida
        # A Direção sempre tem acesso geral
        roles_aceitas = set(allowed_roles)
        roles_aceitas.add(UserRole.DIRECAO.value)

        if current_user.role not in roles_aceitas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Ação restrita aos perfis: {', '.join(allowed_roles)}."
            )
        return current_user

    return role_checker


@router.post("/login", response_model=Token, summary="Login via JSON (E-mail e Senha)")
def login_json(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Autentica o usuário recebendo payload JSON com e-mail e senha."""
    client_ip = request.client.host if request.client else None
    email_clean = credentials.email.strip().lower()

    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(credentials.senha, user.senha_hash):
        registrar_auditoria(
            db=db,
            acao="LOGIN_FALHA",
            entidade="User",
            registro_id=str(user.id) if user else None,
            detalhes={"email": email_clean, "motivo": "Credenciais incorretas"},
            usuario=user,
            usuario_email=email_clean,
            ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.ativo:
        registrar_auditoria(
            db=db,
            acao="LOGIN_BLOQUEADO",
            entidade="User",
            registro_id=str(user.id),
            detalhes={"email": email_clean, "motivo": "Conta inativa"},
            usuario=user,
            ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Entre em contato com a Direção da escola."
        )

    if user.role == UserRole.PROFESSOR.value and not user.professor_id:
        t = db.query(Teacher).filter((Teacher.user_id == user.id) | (Teacher.email == user.email)).first()
        if t:
            user.professor_id = t.id
            t.user_id = user.id
            db.commit()
            db.refresh(user)

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role}
    )

    registrar_auditoria(
        db=db,
        acao="LOGIN_SUCESSO",
        entidade="User",
        registro_id=str(user.id),
        detalhes={"email": user.email, "role": user.role},
        usuario=user,
        ip=client_ip
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        usuario=UserResponse.model_validate(user)
    )


@router.post("/login-form", response_model=Token, summary="Login via OAuth2 Form Data (Swagger)")
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Autentica o usuário via formulário OAuth2 (compatível com botão Authorize do Swagger)."""
    return login_json(
        credentials=UserLogin(email=form_data.username, senha=form_data.password),
        request=request,
        db=db
    )


@router.get("/me", response_model=UserResponse, summary="Obter dados do usuário logado")
def read_current_user_me(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna os dados cadastrais e perfil do usuário autenticado atual."""
    return UserResponse.model_validate(current_user)
