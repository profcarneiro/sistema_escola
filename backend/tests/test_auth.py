from app.core.security import get_password_hash
from app.models.user import User, UserRole


def deve_realizar_login_com_sucesso_via_json(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hbartes.com", "senha": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["usuario"]["email"] == "admin@hbartes.com"
    assert data["usuario"]["role"] == "Direção"
    assert "senha_hash" not in data["usuario"]


def deve_realizar_login_com_sucesso_via_oauth2_form(client):
    response = client.post(
        "/api/v1/auth/login-form",
        data={"username": "admin@hbartes.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["usuario"]["email"] == "admin@hbartes.com"


def deve_rejeitar_login_com_senha_incorreta(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hbartes.com", "senha": "senha_errada"}
    )
    assert response.status_code == 401
    assert "E-mail ou senha incorretos" in response.json()["detail"]


def deve_rejeitar_login_com_email_inexistente(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inexistente@hbartes.com", "senha": "qualquersenhainvalida"}
    )
    assert response.status_code == 401
    assert "E-mail ou senha incorretos" in response.json()["detail"]


def deve_bloquear_login_de_usuario_inativo(client, db_session):
    usuario_inativo = User(
        nome="Inativo Teste",
        email="inativo@hbartes.com",
        senha_hash=get_password_hash("senha123"),
        role=UserRole.SECRETARIA.value,
        ativo=False
    )
    db_session.add(usuario_inativo)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inativo@hbartes.com", "senha": "senha123"}
    )
    assert response.status_code == 403
    assert "inativo" in response.json()["detail"].lower()


def deve_obter_dados_do_usuario_autenticado_em_me(client, admin_token):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@hbartes.com"
    assert data["nome"] == "Helena Barufaldi (Direção)"
    assert data["role"] == "Direção"


def deve_rejeitar_me_sem_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "não fornecido" in response.json()["detail"]


def deve_rejeitar_me_com_token_invalido(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token_completamente_falso_e_invalido"}
    )
    assert response.status_code == 401
    assert "inválido ou expirado" in response.json()["detail"]
