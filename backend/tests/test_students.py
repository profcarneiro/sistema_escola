from datetime import date


def deve_cadastrar_aluno_maior_de_idade_sem_responsavel(client, admin_token):
    payload = {
        "nome": "Lucas Martins (Adulto)",
        "data_nascimento": "1995-05-10",  # Adulto (> 18 anos)
        "cpf": "123.456.789-00",
        "email": "lucas.martins@exemplo.com",
        "telefone": "(19) 98888-7777",
        "endereco": "Rua Central, 50 - Nova Odessa",
        "alergias": "Nenhuma",
        "autorizacao_imagem": True
    }
    resp = client.post(
        "/api/v1/students/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Lucas Martins (Adulto)"
    assert data["responsavel"] is None
    assert data["ativo"] is True


def deve_cadastrar_aluno_menor_com_responsavel(client, admin_token):
    payload = {
        "nome": "Sofia Ferreira (Infantil)",
        "data_nascimento": "2017-08-15",  # Criança (< 18 anos)
        "autorizacao_imagem": True,
        "alergias": "Rinite e pólen",
        "responsavel": {
            "nome": "Juliana Ferreira (Mãe)",
            "cpf": "333.444.555-66",
            "telefone": "(19) 97777-6666",
            "email": "juliana.ferreira@exemplo.com",
            "endereco": "Av. Brasil, 200 - Nova Odessa/SP"
        }
    }
    resp = client.post(
        "/api/v1/students/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Sofia Ferreira (Infantil)"
    assert data["responsavel"] is not None
    assert data["responsavel"]["nome"] == "Juliana Ferreira (Mãe)"
    assert data["responsavel"]["cpf"] == "333.444.555-66"
    assert data["responsavel"]["responsavel_financeiro"] is True


def deve_rejeitar_aluno_menor_sem_responsavel(client, admin_token):
    # Regra Crítica: menor SEM responsável deve ser rejeitado com 422
    payload = {
        "nome": "Menor Sem Responsavel",
        "data_nascimento": "2018-01-01",  # Menor de idade
        "responsavel": None
    }
    resp = client.post(
        "/api/v1/students/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422
    assert "responsável" in resp.text.lower()


def deve_rejeitar_adicao_de_segundo_responsavel(client, admin_token):
    # 1. Cria aluno com responsável
    payload = {
        "nome": "Gabriel Lima",
        "data_nascimento": "2016-04-12",
        "responsavel": {
            "nome": "Marcos Lima (Pai)",
            "cpf": "111.222.333-44",
            "telefone": "(19) 99111-2222",
            "email": "marcos.lima@exemplo.com",
            "endereco": "Rua 1, 100"
        }
    }
    cria_resp = client.post("/api/v1/students/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert cria_resp.status_code == 201
    aluno_id = cria_resp.json()["id"]

    # 2. Tentativa de cadastrar 2º responsável (REGRA EXPLÍCITA: Aluno só pode ter UM responsável)
    resp2 = client.post(
        f"/api/v1/students/{aluno_id}/responsavel",
        json={
            "nome": "Ana Lima (Mãe)",
            "cpf": "999.888.777-66",
            "telefone": "(19) 99333-4444",
            "email": "ana.lima@exemplo.com",
            "endereco": "Rua 1, 100"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp2.status_code == 409
    assert "não pode ter mais de um responsável" in resp2.json()["detail"].lower()


def deve_permitir_adicionar_responsavel_a_aluno_que_nao_possuia(client, admin_token):
    # Cria aluno adulto sem responsável
    payload = {
        "nome": "Aluno Adulto Inicial",
        "data_nascimento": "1990-01-01",
        "cpf": "555.666.777-88"
    }
    cria_resp = client.post("/api/v1/students/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert cria_resp.status_code == 201
    aluno_id = cria_resp.json()["id"]

    # Agora vincula um responsável financeiro
    resp = client.post(
        f"/api/v1/students/{aluno_id}/responsavel",
        json={
            "nome": "Patrocinador Financeiro",
            "cpf": "777.888.999-00",
            "telefone": "(19) 98111-0000",
            "email": "patrocinador@exemplo.com",
            "endereco": "Rua Teste, 10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Patrocinador Financeiro"


def deve_listar_alunos_com_filtro_menor_de_idade(client, admin_token):
    resp = client.get("/api/v1/students/?menor_de_idade=true", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    alunos = resp.json()
    assert isinstance(alunos, list)


def deve_obter_aluno_por_id_com_detalhes(client, admin_token):
    payload = {
        "nome": "Mariana Consulta",
        "data_nascimento": "1998-10-20",
        "cpf": "888.999.000-11"
    }
    cria = client.post("/api/v1/students/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    aluno_id = cria.json()["id"]

    resp = client.get(f"/api/v1/students/{aluno_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Mariana Consulta"


def deve_atualizar_dados_e_saude_do_aluno(client, admin_token):
    payload = {
        "nome": "Aluno Atualizacao",
        "data_nascimento": "2000-02-02"
    }
    cria = client.post("/api/v1/students/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    aluno_id = cria.json()["id"]

    update_payload = {
        "alergias": "Alergia a tinta acrílica",
        "medicacoes": "Anti-histamínico em caso de crise",
        "autorizacao_imagem": True
    }
    resp = client.put(f"/api/v1/students/{aluno_id}", json=update_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["alergias"] == "Alergia a tinta acrílica"
    assert resp.json()["autorizacao_imagem"] is True


def deve_preservar_data_nascimento_exata_e_excluir_ou_desativar_aluno(client, admin_token, db_session):
    from datetime import date
    from app.models.room import Room
    from app.models.course import Course
    from app.models.teacher import Teacher
    from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
    from app.models.enrollment import Matricula, StatusMatricula

    cria = client.post(
        "/api/v1/students/",
        json={
            "nome": "Aluno Data Exata",
            "data_nascimento": "2000-01-01",
            "autorizacao_imagem": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cria.status_code == 201
    assert cria.json()["data_nascimento"] == "2000-01-01"
    aluno_livre_id = cria.json()["id"]

    # Sem vínculos: deve excluir fisicamente
    del_livre = client.delete(
        f"/api/v1/students/{aluno_livre_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_livre.status_code == 200
    assert "excluído" in del_livre.json()["mensagem"].lower()
    assert client.get(
        f"/api/v1/students/{aluno_livre_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    ).status_code == 404

    # Aluno com matrícula vinculada: deve desativar preservando histórico
    cria2 = client.post(
        "/api/v1/students/",
        json={"nome": "Aluno Vinculado Delete", "data_nascimento": "2001-03-10", "autorizacao_imagem": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    aluno_vinc_id = cria2.json()["id"]

    sala = Room(nome="Sala Del Aluno", capacidade=9, ativa=True)
    curso = Course(nome="Curso Del Aluno", valor_mensalidade=250.0, ativo=True)
    prof = Teacher(nome="Prof Del Aluno", email="prof.del.aluno@hbartes.com", ativo=True)
    db_session.add_all([sala, curso, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Turma Del Aluno",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.SEGUNDA.value,
        turno=Turno.MANHA.value,
        horario_inicio="09:00",
        horario_fim="11:00",
        capacidade_maxima=9,
        ativa=True,
    )
    db_session.add(turma)
    db_session.commit()

    mat = Matricula(
        aluno_id=aluno_vinc_id,
        turma_id=turma.id,
        status=StatusMatricula.ATIVA.value,
        data_matricula=date(2026, 11, 1),
        data_inicio=date(2026, 11, 5),
        valor_mensalidade=250.0,
    )
    db_session.add(mat)
    db_session.commit()

    del_vinc = client.delete(
        f"/api/v1/students/{aluno_vinc_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_vinc.status_code == 200
    assert "desativado" in del_vinc.json()["mensagem"].lower()
    get_vinc = client.get(f"/api/v1/students/{aluno_vinc_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_vinc.status_code == 200
    assert get_vinc.json()["ativo"] is False
