from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# Normaliza protocolo de banco de dados (ex: Supabase e Render fornecem postgres://)
database_url = settings.DATABASE_URL.strip().strip("'\"")

if database_url.startswith("https://") or database_url.startswith("http://"):
    raise ValueError(
        "\n" + "=" * 76 + "\n"
        "❌ ERRO NA CONFIGURAÇÃO DO DATABASE_URL:\n"
        "Você configurou a URL da API Web do Supabase (iniciada com https://) "
        "no lugar da URI de conexão do PostgreSQL!\n\n"
        "A biblioteca de banco de dados (SQLAlchemy) requer uma URI de PostgreSQL que "
        "comece com 'postgresql://' ou 'postgres://'.\n\n"
        "👉 ONDE OBTER A URI CORRETA NO SUPABASE:\n"
        "1. No painel do seu projeto no Supabase, clique no botão 'Connect' (no topo da tela)\n"
        "   ou vá em 'Project Settings' (ícone de engrenagem) -> 'Database'.\n"
        "2. Na seção 'Connection string', clique na aba 'URI'.\n"
        "3. Selecione o modo 'Transaction' (Connection Pooler na porta 6543).\n"
        "4. A URL correta tem o formato:\n"
        "   postgresql://postgres.[PROJECT_REF]:[SUA_SENHA]@aws-0-[REGION].pooler.supabase.com:6543/postgres\n\n"
        "5. No Render -> Environment, substitua o valor de DATABASE_URL pela URI acima.\n"
        "=" * 76 + "\n"
    )

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configuração do Engine conforme o dialeto
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=False
    )

    # Ativar foreign keys e modo WAL para integridade e concorrência no SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
else:
    # PostgreSQL / Supabase: pooling robusto e verificação de conexão ativa
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI para obter sessão com o banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

