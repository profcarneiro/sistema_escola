from app.models.course import Course


def deve_criar_modalidade_artistica(client, admin_token):
    resp = client.post(
        "/api/v1/courses/",
        json={"nome": "Aquarela Avançada", "duracao_meses": 12, "valor_mensalidade": 300.0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Aquarela Avançada"
    assert data["valor_mensalidade"] == 300.0
    assert data["ativo"] is True


def deve_listar_cursos_ativos(client, admin_token, db_session):
    db_session.add(Course(nome="Mangá Iniciante", duracao_meses=12, valor_mensalidade=260.0, ativo=True))
    db_session.add(Course(nome="Óleo Clássico", duracao_meses=12, valor_mensalidade=290.0, ativo=True))
    db_session.commit()

    resp = client.get("/api/v1/courses/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    nomes = [c["nome"] for c in resp.json()]
    assert "Mangá Iniciante" in nomes
    assert "Óleo Clássico" in nomes


def deve_rejeitar_curso_duplicado(client, admin_token, db_session):
    db_session.add(Course(nome="Fotografia Básica", valor_mensalidade=300.0, ativo=True))
    db_session.commit()

    resp = client.post(
        "/api/v1/courses/",
        json={"nome": "Fotografia Básica", "valor_mensalidade": 300.0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400


def deve_bloquear_criacao_de_curso_por_professor(client, professor_token):
    resp = client.post(
        "/api/v1/courses/",
        json={"nome": "Curso Não Autorizado", "valor_mensalidade": 200.0},
        headers={"Authorization": f"Bearer {professor_token}"}
    )
    assert resp.status_code == 403


def deve_atualizar_valor_mensalidade_do_curso(client, admin_token, db_session):
    curso = Course(nome="Arteterapia Básica", valor_mensalidade=250.0, ativo=True)
    db_session.add(curso)
    db_session.commit()
    db_session.refresh(curso)

    resp = client.put(
        f"/api/v1/courses/{curso.id}",
        json={"valor_mensalidade": 280.0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["valor_mensalidade"] == 280.0


def deve_obter_curso_por_id(client, admin_token, db_session):
    curso = Course(nome="Desenho Moda Teste", valor_mensalidade=270.0, ativo=True)
    db_session.add(curso)
    db_session.commit()
    db_session.refresh(curso)

    resp = client.get(f"/api/v1/courses/{curso.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Desenho Moda Teste"


def deve_retornar_404_para_curso_inexistente(client, admin_token):
    resp = client.get("/api/v1/courses/99999", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404
