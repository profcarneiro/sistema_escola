from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text, or_

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.audit import registrar_auditoria
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.course import Course
from app.models.class_group import ClassGroup, FaixaEtaria

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIGRATION_P0_TURMAS_ID = "p0_turmas_capacidade_mistas_2026_11"


def _migrar_sqlite_sem_limite_9(target_engine) -> None:
    """Reconstrói tabelas SQLite caso possuam CHECK <= 9 ou NOT NULL legados."""
    with target_engine.connect() as conn:
        rooms_sql_row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='rooms'")
        ).fetchone()
        cg_sql_row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='class_groups'")
        ).fetchone()

    rooms_sql = rooms_sql_row[0] if rooms_sql_row and rooms_sql_row[0] else ""
    cg_sql = cg_sql_row[0] if cg_sql_row and cg_sql_row[0] else ""

    precisa_rooms = "check_capacidade_maxima_9" in rooms_sql or "capacidade <= 9" in rooms_sql
    precisa_cg = (
        "check_turma_capacidade_maxima_9" in cg_sql
        or "capacidade_maxima <= 9" in cg_sql
        or "faixa_etaria VARCHAR(30) NOT NULL" in cg_sql
        or "curso_id INTEGER NOT NULL" in cg_sql
    )

    if not precisa_rooms and not precisa_cg:
        return

    raw_conn = target_engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        # PRAGMA foreign_keys deve ser alterado fora de transação no SQLite
        raw_conn.commit()
        cur.execute("PRAGMA foreign_keys=OFF")
        cur.execute("BEGIN")
        try:
            if precisa_rooms:
                logger.info("Migrando tabela SQLite 'rooms': removendo limite fixo de 9 alunos")
                cur.execute(
                    """
                    CREATE TABLE rooms_new (
                        id INTEGER NOT NULL,
                        nome VARCHAR(50) NOT NULL,
                        capacidade INTEGER NOT NULL,
                        descricao VARCHAR(255),
                        ativa BOOLEAN NOT NULL,
                        criada_em DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        CONSTRAINT check_capacidade_minima_1 CHECK (capacidade >= 1)
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO rooms_new (id, nome, capacidade, descricao, ativa, criada_em)
                    SELECT id, nome, capacidade, descricao, ativa, criada_em FROM rooms
                    """
                )
                cur.execute("DROP TABLE rooms")
                cur.execute("ALTER TABLE rooms_new RENAME TO rooms")
                cur.execute("CREATE INDEX IF NOT EXISTS ix_rooms_id ON rooms (id)")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_rooms_nome ON rooms (nome)")

            if precisa_cg:
                logger.info("Migrando tabela SQLite 'class_groups': removendo limite 9 e ajustando nulabilidade")
                cur.execute(
                    """
                    CREATE TABLE class_groups_new (
                        id INTEGER NOT NULL,
                        nome VARCHAR(100) NOT NULL,
                        curso_id INTEGER,
                        sala_id INTEGER NOT NULL,
                        professor_id INTEGER NOT NULL,
                        faixa_etaria VARCHAR(30),
                        dia_semana VARCHAR(20) NOT NULL,
                        turno VARCHAR(20) NOT NULL,
                        horario_inicio VARCHAR(5) NOT NULL,
                        horario_fim VARCHAR(5) NOT NULL,
                        capacidade_maxima INTEGER NOT NULL,
                        ativa BOOLEAN NOT NULL,
                        criada_em DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        CONSTRAINT check_turma_capacidade_minima_1 CHECK (capacidade_maxima >= 1),
                        FOREIGN KEY(curso_id) REFERENCES courses (id) ON DELETE RESTRICT,
                        FOREIGN KEY(sala_id) REFERENCES rooms (id) ON DELETE RESTRICT,
                        FOREIGN KEY(professor_id) REFERENCES teachers (id) ON DELETE RESTRICT
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO class_groups_new (
                        id, nome, curso_id, sala_id, professor_id, faixa_etaria,
                        dia_semana, turno, horario_inicio, horario_fim,
                        capacidade_maxima, ativa, criada_em
                    )
                    SELECT
                        id, nome, curso_id, sala_id, professor_id, faixa_etaria,
                        dia_semana, turno, horario_inicio, horario_fim,
                        capacidade_maxima, ativa, criada_em
                    FROM class_groups
                    """
                )
                cur.execute("DROP TABLE class_groups")
                cur.execute("ALTER TABLE class_groups_new RENAME TO class_groups")
                cur.execute("CREATE INDEX IF NOT EXISTS ix_class_groups_id ON class_groups (id)")
                cur.execute("CREATE INDEX IF NOT EXISTS ix_class_groups_nome ON class_groups (nome)")

            raw_conn.commit()
        except Exception:
            raw_conn.rollback()
            raise
        finally:
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    finally:
        raw_conn.close()


def aplicar_migracoes(target_engine) -> None:
    """Aplica migrações incrementais seguras (SQLite e PostgreSQL/Supabase)."""
    try:
        with target_engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "id VARCHAR(100) PRIMARY KEY, "
                "applied_at TIMESTAMP NOT NULL)"
            ))

        inspector = inspect(target_engine)
        tables = inspector.get_table_names()

        if "matriculas" in tables:
            cols = [c["name"] for c in inspector.get_columns("matriculas")]
            with target_engine.begin() as conn:
                if "dia_vencimento" not in cols:
                    logger.info("Migrando tabela matriculas: adicionando dia_vencimento")
                    conn.execute(text("ALTER TABLE matriculas ADD COLUMN dia_vencimento INTEGER DEFAULT 10;"))
                if "quantidade_parcelas" not in cols:
                    logger.info("Migrando tabela matriculas: adicionando quantidade_parcelas")
                    conn.execute(text("ALTER TABLE matriculas ADD COLUMN quantidade_parcelas INTEGER DEFAULT 12;"))
                if "curso_id" not in cols:
                    logger.info("Migrando tabela matriculas: adicionando curso_id")
                    conn.execute(text("ALTER TABLE matriculas ADD COLUMN curso_id INTEGER;"))

        if "users" in tables:
            cols = [c["name"] for c in inspector.get_columns("users")]
            with target_engine.begin() as conn:
                if "professor_id" not in cols:
                    logger.info("Migrando tabela users: adicionando professor_id")
                    conn.execute(text("ALTER TABLE users ADD COLUMN professor_id INTEGER;"))

        if target_engine.dialect.name == "sqlite":
            _migrar_sqlite_sem_limite_9(target_engine)
        elif target_engine.dialect.name == "postgresql":
            with target_engine.begin() as conn:
                if "rooms" in tables:
                    conn.execute(text("ALTER TABLE rooms DROP CONSTRAINT IF EXISTS check_capacidade_maxima_9;"))
                    for (conname,) in conn.execute(text(
                        "SELECT c.conname FROM pg_constraint c "
                        "JOIN pg_class t ON c.conrelid = t.oid "
                        "WHERE t.relname = 'rooms' AND c.contype = 'c' "
                        "AND pg_get_constraintdef(c.oid) LIKE '%<= 9%'"
                    )).fetchall():
                        conn.execute(text(f'ALTER TABLE rooms DROP CONSTRAINT IF EXISTS "{conname}";'))
                if "class_groups" in tables:
                    conn.execute(text("ALTER TABLE class_groups DROP CONSTRAINT IF EXISTS check_turma_capacidade_maxima_9;"))
                    for (conname,) in conn.execute(text(
                        "SELECT c.conname FROM pg_constraint c "
                        "JOIN pg_class t ON c.conrelid = t.oid "
                        "WHERE t.relname = 'class_groups' AND c.contype = 'c' "
                        "AND pg_get_constraintdef(c.oid) LIKE '%<= 9%'"
                    )).fetchall():
                        conn.execute(text(f'ALTER TABLE class_groups DROP CONSTRAINT IF EXISTS "{conname}";'))
                    conn.execute(text("ALTER TABLE class_groups ALTER COLUMN faixa_etaria DROP NOT NULL;"))
                    conn.execute(text("ALTER TABLE class_groups ALTER COLUMN curso_id DROP NOT NULL;"))

        # Backfill da tabela associativa N:N class_group_courses e de matriculas.curso_id
        inspector = inspect(target_engine)
        tables = inspector.get_table_names()
        if "class_groups" in tables and "class_group_courses" in tables:
            with target_engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO class_group_courses (turma_id, curso_id) "
                    "SELECT cg.id, cg.curso_id FROM class_groups cg "
                    "WHERE cg.curso_id IS NOT NULL "
                    "AND NOT EXISTS ("
                    "  SELECT 1 FROM class_group_courses cgc "
                    "  WHERE cgc.turma_id = cg.id AND cgc.curso_id = cg.curso_id"
                    ")"
                ))
        if "matriculas" in tables and "class_groups" in tables:
            with target_engine.begin() as conn:
                conn.execute(text(
                    "UPDATE matriculas SET curso_id = ("
                    "  SELECT cg.curso_id FROM class_groups cg WHERE cg.id = matriculas.turma_id"
                    ") WHERE curso_id IS NULL"
                ))
    except Exception as e:
        logger.warning(f"Aviso ao aplicar migrações automáticas: {e}")


def aplicar_correcoes_dados_p0(db: Session) -> None:
    """
    Executa uma única vez os ajustes de dados P0 no banco ativo (SQLite ou Supabase/PostgreSQL):
    - Move 'Desenho Artístico módulo 1 - Ana Júlia - Terça 14:30' da Sala 1 para a Sala 3.
    - Limpa a faixa etária salva automaticamente como 'INFANTIL' nessa turma e em
      'Pintura em Aquarela - Helena - Quarta 14:00', exigindo seleção explícita.
    """
    try:
        ja_aplicada = db.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": MIGRATION_P0_TURMAS_ID}
        ).fetchone()
        if ja_aplicada:
            return

        sala_3 = db.query(Room).filter(Room.nome.ilike("Sala 3")).first()

        turma_ana = (
            db.query(ClassGroup)
            .filter(ClassGroup.nome.ilike("%Desenho Artístico%Ana Júlia%Terça%14:30%"))
            .first()
        )
        if not turma_ana:
            turma_ana = (
                db.query(ClassGroup)
                .filter(ClassGroup.nome.ilike("%Desenho Artístico%Ana Júlia%"))
                .first()
            )
        if not turma_ana:
            turma_ana = (
                db.query(ClassGroup)
                .filter(
                    ClassGroup.nome.ilike("%Ana Júlia%"),
                    ClassGroup.dia_semana == "TERCA",
                    ClassGroup.horario_inicio == "14:30",
                )
                .first()
            )

        if turma_ana:
            if sala_3 and turma_ana.sala_id != sala_3.id:
                logger.info(f"Migração P0: movendo turma '{turma_ana.nome}' (id={turma_ana.id}) para Sala 3 (id={sala_3.id}).")
                turma_ana.sala_id = sala_3.id
            if turma_ana.faixa_etaria == FaixaEtaria.INFANTIL.value:
                logger.info(f"Migração P0: limpando faixa_etaria='INFANTIL' automática da turma '{turma_ana.nome}' (id={turma_ana.id}).")
                turma_ana.faixa_etaria = None

        turma_helena = (
            db.query(ClassGroup)
            .filter(ClassGroup.nome.ilike("%Pintura em Aquarela%Helena%Quarta%14:00%"))
            .first()
        )
        if not turma_helena:
            turma_helena = (
                db.query(ClassGroup)
                .filter(ClassGroup.nome.ilike("%Pintura em Aquarela%Helena%"))
                .first()
            )
        if not turma_helena:
            turma_helena = (
                db.query(ClassGroup)
                .filter(
                    or_(
                        ClassGroup.nome.ilike("%Aquarela%Helena%"),
                        ClassGroup.nome.ilike("%Pintura%Helena%"),
                    ),
                    ClassGroup.dia_semana == "QUARTA",
                    ClassGroup.horario_inicio == "14:00",
                )
                .first()
            )

        if turma_helena and turma_helena.faixa_etaria == FaixaEtaria.INFANTIL.value:
            logger.info(f"Migração P0: limpando faixa_etaria='INFANTIL' automática da turma '{turma_helena.nome}' (id={turma_helena.id}).")
            turma_helena.faixa_etaria = None

        db.execute(
            text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
            {"id": MIGRATION_P0_TURMAS_ID, "applied_at": datetime.now(timezone.utc)}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Aviso ao aplicar correções de dados P0: {e}")


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

    # --- Correções de dados P0 (idempotente) ---
    aplicar_correcoes_dados_p0(db)


def main() -> None:
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
