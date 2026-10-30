import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.audit import registrar_auditoria
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    """Cria tabelas se não existirem e garante o usuário administrador padrão."""
    # Garante que as tabelas existem
    Base.metadata.create_all(bind=engine)

    admin_email = settings.FIRST_SUPERUSER_EMAIL.strip().lower()
    user = db.query(User).filter(User.email == admin_email).first()

    if not user:
        logger.info(f"Criando usuário administrador inicial: {admin_email}")
        user = User(
            nome=settings.FIRST_SUPERUSER_NAME,
            email=admin_email,
            senha_hash=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            role=UserRole.DIRECAO.value,
            ativo=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        registrar_auditoria(
            db=db,
            acao="SISTEMA_INICIALIZADO",
            entidade="User",
            registro_id=str(user.id),
            detalhes={"email": user.email, "role": user.role, "mensagem": "Usuário Direção inicial criado"},
            usuario=user
        )
        logger.info("Usuário administrador inicial criado com sucesso.")
    else:
        logger.info(f"Usuário administrador {admin_email} já existe no banco de dados.")


def main() -> None:
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
