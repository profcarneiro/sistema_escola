import logging
from sqlalchemy.orm import Session

from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.security import get_password_hash
from app.core.audit import registrar_auditoria
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.course import Course

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def aplicar_migracoes(engine) -> None:
    """Aplica migrações incrementais seguras (ALTER TABLE) caso as colunas novas ainda não existam."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "matriculas" in tables:
            cols = [c["name"] for c in inspector.get_columns("matriculas")]
            with engine.begin() as conn:
                if "dia_vencimento" not in cols:
                    logger.info("Migrando tabela matriculas: adicionando dia_vencimento")
                    conn.execute(text("ALTER TABLE matriculas ADD COLUMN dia_vencimento INTEGER DEFAULT 10;"))
                if "quantidade_parcelas" not in cols:
                    logger.info("Migrando tabela matriculas: adicionando quantidade_parcelas")
                    conn.execute(text("ALTER TABLE matriculas ADD COLUMN quantidade_parcelas INTEGER DEFAULT 12;"))

        if "users" in tables:
            cols = [c["name"] for c in inspector.get_columns("users")]
            with engine.begin() as conn:
                if "professor_id" not in cols:
                    logger.info("Migrando tabela users: adicionando professor_id")
                    conn.execute(text("ALTER TABLE users ADD COLUMN professor_id INTEGER;"))
    except Exception as e:
        logger.warning(f"Aviso ao aplicar migrações automáticas: {e}")


SALAS_PADRAO = [
    {"nome": "Sala 1", "capacidade": 9, "descricao": "Sala multiuso de artes"},
    {"nome": "Sala 2", "capacidade": 9, "descricao": "Sala de pintura e aquarela"},
    {"nome": "Sala 3", "capacidade": 9, "descricao": "Sala de desenho"},
    {"nome": "Sala 4", "capacidade": 9, "descricao": "Sala de fotografia e digital"},
    {"nome": "Sala 5", "capacidade": 9, "descricao": "Sala de mangá e quadrinhos"},
    {"nome": "Sala 6", "capacidade": 9, "descricao": "Sala de arteterapia"},
]

CURSOS_PADRAO = [
    {"nome": "Desenho Publicitário", "descricao": "Técnicas de desenho aplicado à publicidade e comunicação visual.", "duracao_meses": 12, "valor_mensalidade": 280.0},
    {"nome": "Desenho Artístico", "descricao": "Fundamentos e técnicas do desenho artístico clássico e contemporâneo.", "duracao_meses": 12, "valor_mensalidade": 260.0},
    {"nome": "Desenho Moda", "descricao": "Desenho técnico e artístico voltado à área da moda e vestuário.", "duracao_meses": 12, "valor_mensalidade": 270.0},
    {"nome": "Desenho Infantil", "descricao": "Arte e criatividade para crianças — traço, cor e expressão.", "duracao_meses": 6, "valor_mensalidade": 230.0},
    {"nome": "Óleo sobre tela", "descricao": "Técnica clássica de pintura em tela com tinta a óleo.", "duracao_meses": 12, "valor_mensalidade": 290.0},
    {"nome": "Aquarela", "descricao": "Arte da aquarela — transparência, luz e cor na água.", "duracao_meses": 12, "valor_mensalidade": 260.0},
    {"nome": "Arteterapia", "descricao": "Arte como ferramenta terapêutica e de bem-estar emocional.", "duracao_meses": 6, "valor_mensalidade": 250.0},
    {"nome": "Fotografia", "descricao": "Fundamentos de fotografia — composição, luz e narrativa visual.", "duracao_meses": 12, "valor_mensalidade": 300.0},
    {"nome": "Mangá", "descricao": "Técnicas de desenho no estilo japonês — personagens, perspectiva e roteiro.", "duracao_meses": 12, "valor_mensalidade": 260.0},
]


def init_db(db: Session) -> None:
    """Cria tabelas se não existirem e garante o usuário administrador padrão e dados iniciais."""
    Base.metadata.create_all(bind=engine)
    aplicar_migracoes(engine)

    # --- Usuário administrador ---
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

    # --- Salas padrão ---
    for sala_data in SALAS_PADRAO:
        existente = db.query(Room).filter(Room.nome == sala_data["nome"]).first()
        if not existente:
            nova_sala = Room(**sala_data, ativa=True)
            db.add(nova_sala)
            logger.info(f"Sala criada: {sala_data['nome']}")
    db.commit()

    # --- Cursos padrão ---
    for curso_data in CURSOS_PADRAO:
        existente = db.query(Course).filter(Course.nome == curso_data["nome"]).first()
        if not existente:
            novo_curso = Course(**curso_data, ativo=True)
            db.add(novo_curso)
            logger.info(f"Curso criado: {curso_data['nome']}")
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

