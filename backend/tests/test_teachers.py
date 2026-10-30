from app.models.teacher import Teacher


def deve_criar_professor_com_especialidades(client, admin_token):
    resp = client.post(
        "/api/v1/teachers/",
        json={
            "nome": "Prof. Carlos Alves",
            "email": "carlos.alves@hbartes.com",
            "telefone": "(19) 99999-0001",
            "endereco": "Rua das Flores, 100 - Nova Odessa/SP",
            "especialidades": "Aquarela, Óleo sobre tela",
            "disponibilidade": "Terça tarde, Quinta manhã, Sábado manhã"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Prof. Carlos Alves"
    assert data["especialidades"] == "Aquarela, Óleo sobre tela"
    assert data["ativo"] is True


def deve_rejeitar_professor_com_email_duplicado(client, admin_token, db_session):
    professor = Teacher(nome="Prof Duplicado", email="duplicado@hbartes.com", ativo=True)
    db_session.add(professor)
    db_session.commit()

    resp = client.post(
        "/api/v1/teachers/",
        json={"nome": "Outro Prof", "email": "duplicado@hbartes.com"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400


def deve_criar_professor_com_substituto(client, admin_token, db_session):
    substituto = Teacher(nome="Prof Substituto", email="substituto@hbartes.com", ativo=True)
    db_session.add(substituto)
    db_session.commit()
    db_session.refresh(substituto)

    resp = client.post(
        "/api/v1/teachers/",
        json={
            "nome": "Prof Principal",
            "email": "principal@hbartes.com",
            "substituto_id": substituto.id
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    assert resp.json()["substituto_id"] == substituto.id


def deve_rejeitar_substituto_inexistente(client, admin_token):
    resp = client.post(
        "/api/v1/teachers/",
        json={"nome": "Prof Invalido", "email": "invalido@hbartes.com", "substituto_id": 99999},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 404


def deve_listar_professores_ativos(client, admin_token, db_session):
    db_session.add(Teacher(nome="Prof Listagem A", email="lista.a@hbartes.com", ativo=True))
    db_session.add(Teacher(nome="Prof Listagem B", email="lista.b@hbartes.com", ativo=True))
    db_session.commit()

    resp = client.get("/api/v1/teachers/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def deve_obter_professor_por_id(client, admin_token, db_session):
    prof = Teacher(nome="Prof ID Teste", email="idteste@hbartes.com", ativo=True)
    db_session.add(prof)
    db_session.commit()
    db_session.refresh(prof)

    resp = client.get(f"/api/v1/teachers/{prof.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Prof ID Teste"


def deve_atualizar_disponibilidade_professor(client, admin_token, db_session):
    prof = Teacher(nome="Prof Disponibilidade", email="disponibilidade@hbartes.com", ativo=True)
    db_session.add(prof)
    db_session.commit()
    db_session.refresh(prof)

    resp = client.put(
        f"/api/v1/teachers/{prof.id}",
        json={"disponibilidade": "Sábado manhã e tarde"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["disponibilidade"] == "Sábado manhã e tarde"


def deve_rejeitar_professor_como_proprio_substituto(client, admin_token, db_session):
    prof = Teacher(nome="Prof Circular", email="circular@hbartes.com", ativo=True)
    db_session.add(prof)
    db_session.commit()
    db_session.refresh(prof)

    resp = client.put(
        f"/api/v1/teachers/{prof.id}",
        json={"substituto_id": prof.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
