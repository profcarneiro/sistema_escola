def deve_permitir_direcao_criar_novo_usuario(client, admin_token):
    novo = {
        "nome": "Professor Carlos",
        "email": "carlos.prof@hbartes.com",
        "role": "Professor",
        "ativo": True,
        "senha": "senhaSegura123"
    }
    response = client.post(
        "/api/v1/users/",
        json=novo,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Professor Carlos"
    assert data["email"] == "carlos.prof@hbartes.com"
    assert data["role"] == "Professor"
    assert "senha_hash" not in data


def deve_rejeitar_criacao_de_usuario_com_email_duplicado(client, admin_token):
    duplicado = {
        "nome": "Outro Admin",
        "email": "admin@hbartes.com",
        "role": "Direção",
        "ativo": True,
        "senha": "outrasenha123"
    }
    response = client.post(
        "/api/v1/users/",
        json=duplicado,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Já existe um usuário cadastrado com este e-mail" in response.json()["detail"]


def deve_rejeitar_criacao_de_usuario_por_perfil_nao_direcao(client, professor_token):
    tentativa = {
        "nome": "Novo Aluno Fake",
        "email": "aluno.fake@hbartes.com",
        "role": "Secretaria",
        "ativo": True,
        "senha": "senha123456"
    }
    response = client.post(
        "/api/v1/users/",
        json=tentativa,
        headers={"Authorization": f"Bearer {professor_token}"}
    )
    assert response.status_code == 403
    assert "Acesso negado" in response.json()["detail"]


def deve_permitir_direcao_listar_usuarios(client, admin_token):
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    lista = response.json()
    assert len(lista) >= 1
    assert any(u["email"] == "admin@hbartes.com" for u in lista)


def deve_bloquear_listagem_de_usuarios_para_outros_perfis(client, secretaria_token):
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    assert response.status_code == 403


def deve_permitir_atualizar_dados_de_usuario(client, admin_token):
    # Cria usuário para editar
    create_resp = client.post(
        "/api/v1/users/",
        json={
            "nome": "Financeiro João",
            "email": "joao.fin@hbartes.com",
            "role": "Financeiro",
            "ativo": True,
            "senha": "senha123456"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_resp.json()["id"]

    # Atualiza nome e status
    update_resp = client.put(
        f"/api/v1/users/{user_id}",
        json={"nome": "João Financeiro Atualizado", "ativo": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["nome"] == "João Financeiro Atualizado"
    assert update_resp.json()["ativo"] is False


def deve_impedir_usuario_de_excluir_a_si_mesmo(client, admin_token):
    # O admin tem id 1
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    me_id = me_resp.json()["id"]

    del_resp = client.delete(
        f"/api/v1/users/{me_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_resp.status_code == 400
    assert "Não é permitido excluir o próprio usuário logado" in del_resp.json()["detail"]


def deve_permitir_excluir_outro_usuario(client, admin_token):
    # Cria usuário para deletar
    create_resp = client.post(
        "/api/v1/users/",
        json={
            "nome": "Para Deletar",
            "email": "deletar@hbartes.com",
            "role": "Secretaria",
            "ativo": True,
            "senha": "senha123456"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_resp.status_code == 200
    assert "excluído com sucesso" in del_resp.json()["mensagem"]

    # Confirma que não existe mais
    get_resp = client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_resp.status_code == 404
