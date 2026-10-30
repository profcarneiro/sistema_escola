import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole

# Banco de dados SQLite em memória para testes isolados
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    """Cria uma base de dados limpa para cada teste."""
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()

    # Cria o usuário admin padrão da escola
    admin = User(
        nome="Helena Barufaldi (Direção)",
        email="admin@hbartes.com",
        senha_hash=get_password_hash("admin123"),
        role=UserRole.DIRECAO.value,
        ativo=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP de teste com o banco de dados em memória injetado."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    """Obtém token JWT de autenticação para o administrador (Direção)."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hbartes.com", "senha": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def professor_token(client, db_session):
    """Cria um usuário professor e retorna o token de autenticação."""
    prof = User(
        nome="Professor Silva",
        email="prof.silva@hbartes.com",
        senha_hash=get_password_hash("senha123"),
        role=UserRole.PROFESSOR.value,
        ativo=True,
    )
    db_session.add(prof)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "prof.silva@hbartes.com", "senha": "senha123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def secretaria_token(client, db_session):
    """Cria um usuário secretaria e retorna o token de autenticação."""
    sec = User(
        nome="Secretaria Maria",
        email="maria.secretaria@hbartes.com",
        senha_hash=get_password_hash("senha123"),
        role=UserRole.SECRETARIA.value,
        ativo=True,
    )
    db_session.add(sec)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "maria.secretaria@hbartes.com", "senha": "senha123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
