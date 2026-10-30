def deve_registrar_consentimento_geral_de_maior_de_idade(client, secretaria_token):
    payload = {
        "titular_nome": "Mariana Santos",
        "titular_tipo": "ALUNO",
        "menor_idade": False,
        "termo_tipo": "GERAL",
        "consentido": True,
        "versao_termo": "1.0",
        "observacoes": "Consentimento assinado na matrícula presencial"
    }
    response = client.post(
        "/api/v1/lgpd/consentimentos",
        json=payload,
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titular_nome"] == "Mariana Santos"
    assert data["menor_idade"] is False
    assert data["termo_tipo"] == "GERAL"
    assert data["consentido"] is True
    assert "id" in data
    assert "timestamp" in data


def deve_registrar_consentimento_de_menor_com_responsavel(client, secretaria_token):
    payload = {
        "titular_nome": "Lucas Oliveira (Menor)",
        "titular_tipo": "ALUNO",
        "menor_idade": True,
        "responsavel_nome": "Ana Paula Oliveira (Mãe)",
        "termo_tipo": "IMAGEM",
        "consentido": True,
        "versao_termo": "1.0",
        "observacoes": "Autorização de uso de imagem em redes sociais e eventos"
    }
    response = client.post(
        "/api/v1/lgpd/consentimentos",
        json=payload,
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titular_nome"] == "Lucas Oliveira (Menor)"
    assert data["responsavel_nome"] == "Ana Paula Oliveira (Mãe)"
    assert data["menor_idade"] is True
    assert data["termo_tipo"] == "IMAGEM"


def deve_rejeitar_consentimento_de_menor_sem_responsavel(client, secretaria_token):
    payload = {
        "titular_nome": "Pedro Silva (Menor sem responsável)",
        "titular_tipo": "ALUNO",
        "menor_idade": True,
        "responsavel_nome": None,  # Inválido para menor!
        "termo_tipo": "SAUDE",
        "consentido": True,
        "versao_termo": "1.0"
    }
    response = client.post(
        "/api/v1/lgpd/consentimentos",
        json=payload,
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    # Validador Pydantic ou rota rejeita com 422
    assert response.status_code == 422
    assert "responsável" in response.text.lower()


def deve_permitir_listar_consentimentos_com_filtros(client, secretaria_token):
    # Registra dois
    client.post(
        "/api/v1/lgpd/consentimentos",
        json={
            "titular_nome": "Ana Beatriz",
            "titular_tipo": "ALUNO",
            "menor_idade": False,
            "termo_tipo": "GERAL",
            "consentido": True
        },
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    client.post(
        "/api/v1/lgpd/consentimentos",
        json={
            "titular_nome": "Gabriel Lima",
            "titular_tipo": "ALUNO",
            "menor_idade": True,
            "responsavel_nome": "Roberto Lima",
            "termo_tipo": "SAUDE",
            "consentido": True
        },
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )

    # Filtra por menor_idade=True
    response = client.get(
        "/api/v1/lgpd/consentimentos?menor_idade=true",
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    assert response.status_code == 200
    dados = response.json()
    assert all(item["menor_idade"] is True for item in dados)


def deve_permitir_revogar_consentimento_com_motivo(client, secretaria_token):
    # Cria consentimento inicial
    cria_resp = client.post(
        "/api/v1/lgpd/consentimentos",
        json={
            "titular_nome": "Fernanda Souza",
            "titular_tipo": "ALUNO",
            "menor_idade": False,
            "termo_tipo": "IMAGEM",
            "consentido": True
        },
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    consent_id = cria_resp.json()["id"]

    # Revoga
    revoga_resp = client.post(
        f"/api/v1/lgpd/consentimentos/{consent_id}/revogar",
        json={"motivo": "Solicitação do titular para não divulgar fotos no Instagram"},
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    assert revoga_resp.status_code == 200
    assert revoga_resp.json()["consentido"] is False
    assert "REVOGADO" in revoga_resp.json()["observacoes"]


def deve_rejeitar_acesso_a_consentimentos_sem_autenticacao(client):
    response = client.get("/api/v1/lgpd/consentimentos")
    assert response.status_code == 401


def deve_bloquear_professor_de_listar_consentimentos_lgpd(client, professor_token):
    response = client.get(
        "/api/v1/lgpd/consentimentos",
        headers={"Authorization": f"Bearer {professor_token}"}
    )
    assert response.status_code == 403
    assert "Acesso negado" in response.json()["detail"]

