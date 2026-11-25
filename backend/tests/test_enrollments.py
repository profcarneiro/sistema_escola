import pytest
from datetime import date
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.models.student import Aluno
from app.models.enrollment import Matricula, StatusMatricula


@pytest.fixture
def turma_fase3(db_session):
    sala = Room(nome="Sala Matrículas F3", capacidade=9, ativa=True)
    curso = Course(nome="Óleo Sobre Tela F3", valor_mensalidade=290.0, ativo=True)
    prof = Teacher(nome="Prof Matrículas", email="prof.mat@hbartes.com", ativo=True)
    db_session.add_all([sala, curso, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Óleo Sábado Manhã",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.SABADO.value,
        turno=Turno.MANHA.value,
        horario_inicio="09:00",
        horario_fim="11:00",
        capacidade_maxima=9,
        ativa=True
    )
    db_session.add(turma)
    db_session.commit()
    db_session.refresh(turma)
    return turma


@pytest.fixture
def aluno_fase3(db_session):
    aluno = Aluno(
        nome="Aluno Teste Matrícula",
        data_nascimento=date(1996, 3, 15),
        cpf="999.888.777-11",
        email="aluno.teste@hbartes.com",
        ativo=True
    )
    db_session.add(aluno)
    db_session.commit()
    db_session.refresh(aluno)
    return aluno


def deve_matricular_aluno_com_sucesso(client, admin_token, turma_fase3, aluno_fase3):
    payload = {
        "aluno_id": aluno_fase3.id,
        "turma_id": turma_fase3.id,
        "data_matricula": "2026-11-01",
        "data_inicio": "2026-11-05",
        "valor_mensalidade": 290.0,
        "desconto_percentual": 0.0,
        "aula_experimental": False
    }
    resp = client.post("/api/v1/enrollments/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["aluno_id"] == aluno_fase3.id
    assert data["turma_id"] == turma_fase3.id
    assert data["status"] == "ATIVA"
    assert data["numero_contrato"].startswith("MAT-")
    assert data["contrato_assinado"] is False  # Renovação / Contrato não é automático


def deve_rejeitar_segunda_matricula_ativa_na_mesma_turma(client, admin_token, turma_fase3, aluno_fase3):
    payload = {
        "aluno_id": aluno_fase3.id,
        "turma_id": turma_fase3.id,
        "data_matricula": "2026-11-01",
        "data_inicio": "2026-11-05",
        "valor_mensalidade": 290.0
    }
    resp1 = client.post("/api/v1/enrollments/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp1.status_code == 201

    # Segunda tentativa na mesma turma
    resp2 = client.post("/api/v1/enrollments/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp2.status_code == 409
    assert "já possui matrícula ativa" in resp2.json()["detail"].lower()


def deve_rejeitar_decimo_aluno_em_turma_com_capacidade_9(client, admin_token, turma_fase3, db_session):
    """
    REGRA CRÍTICA DO BRIEFING:
    Capacidade máxima da turma/sala é 9.
    Ao tentar matricular o 10º aluno, o sistema DEVE REJEITAR (409).
    """
    alunos = []
    for i in range(1, 11):  # 10 alunos
        a = Aluno(
            nome=f"Aluno Lote {i}",
            data_nascimento=date(1990, 1, 1),
            cpf=f"111.222.333-{i:02d}",
            ativo=True
        )
        db_session.add(a)
        alunos.append(a)
    db_session.commit()

    # Matricula os primeiros 9 com sucesso
    for i in range(9):
        resp = client.post(
            "/api/v1/enrollments/",
            json={
                "aluno_id": alunos[i].id,
                "turma_id": turma_fase3.id,
                "data_matricula": "2026-11-01",
                "data_inicio": "2026-11-05",
                "valor_mensalidade": 290.0
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 201

    # Tentativa de matricular o 10º aluno na turma com capacidade 9
    resp_10 = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": alunos[9].id,
            "turma_id": turma_fase3.id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 290.0
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_10.status_code == 409
    assert "capacidade máxima atingida" in resp_10.json()["detail"].lower()
    assert "lista de espera" in resp_10.json()["detail"].lower()


def deve_aplicar_descontos_irmao_indicacao_bolsa(client, admin_token, turma_fase3, db_session):
    aluno_desc = Aluno(
        nome=f"Aluno Com Desconto",
        data_nascimento=date(1992, 5, 20),
        ativo=True
    )
    db_session.add(aluno_desc)
    db_session.commit()

    payload = {
        "aluno_id": aluno_desc.id,
        "turma_id": turma_fase3.id,
        "data_matricula": "2026-11-01",
        "data_inicio": "2026-11-05",
        "valor_mensalidade": 200.0,
        "desconto_percentual": 15.0,  # 15% de desconto
        "tipo_desconto": "irmao"
    }
    resp = client.post("/api/v1/enrollments/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["desconto_percentual"] == 15.0
    assert data["tipo_desconto"] == "irmao"
    assert data["valor_com_desconto"] == 170.0  # 200 - 15%


def deve_rejeitar_tipo_desconto_invalido(client, admin_token, turma_fase3, aluno_fase3):
    payload = {
        "aluno_id": aluno_fase3.id,
        "turma_id": turma_fase3.id,
        "data_matricula": "2026-11-01",
        "data_inicio": "2026-11-05",
        "valor_mensalidade": 200.0,
        "tipo_desconto": "desconto_inventado"  # inválido
    }
    resp = client.post("/api/v1/enrollments/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_adicionar_aluno_a_lista_de_espera(client, admin_token, turma_fase3, aluno_fase3):
    payload = {
        "aluno_id": aluno_fase3.id,
        "turma_id": turma_fase3.id,
        "observacoes": "Prefere aula aos sábados"
    }
    resp = client.post("/api/v1/enrollments/waitlist", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["aluno_id"] == aluno_fase3.id
    assert data["turma_id"] == turma_fase3.id
    assert data["posicao"] == 1
    assert data["ativa"] is True


def deve_rejeitar_adicionar_aluno_duplicado_na_mesma_lista_de_espera(client, admin_token, turma_fase3, aluno_fase3):
    payload = {
        "aluno_id": aluno_fase3.id,
        "turma_id": turma_fase3.id
    }
    resp1 = client.post("/api/v1/enrollments/waitlist", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/enrollments/waitlist", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp2.status_code == 409
    assert "já está na lista de espera" in resp2.json()["detail"].lower()


def deve_cancelar_matricula_exigindo_motivo(client, admin_token, turma_fase3, aluno_fase3):
    # Cria matrícula
    cria = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": aluno_fase3.id,
            "turma_id": turma_fase3.id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 290.0
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    mat_id = cria.json()["id"]

    # Tentativa de cancelar sem motivo → deve falhar
    resp_sem_motivo = client.put(
        f"/api/v1/enrollments/{mat_id}",
        json={"status": "CANCELADA"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_sem_motivo.status_code == 422

    # Cancelamento com motivo e multa contratual
    resp_com_motivo = client.put(
        f"/api/v1/enrollments/{mat_id}",
        json={
            "status": "CANCELADA",
            "motivo_cancelamento": "Mudança de cidade para Campinas",
            "multa_cancelamento": 50.0
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_com_motivo.status_code == 200
    assert resp_com_motivo.json()["status"] == "CANCELADA"
    assert resp_com_motivo.json()["motivo_cancelamento"] == "Mudança de cidade para Campinas"
    assert resp_com_motivo.json()["multa_cancelamento"] == 50.0


def deve_matricular_acima_de_9_alunos_e_escolher_curso_em_turma_mista(client, admin_token, db_session):
    from app.models.teacher import Teacher
    sala = Room(nome="Ateliê Amplo F3", capacidade=12, ativa=True)
    curso1 = Course(nome="Desenho Artístico M1 F3", valor_mensalidade=260.0, ativo=True)
    curso2 = Course(nome="Mangá F3", valor_mensalidade=275.0, ativo=True)
    prof = Teacher(nome="Prof Misto F3", email="prof.misto.f3@hbartes.com", ativo=True)
    db_session.add_all([sala, curso1, curso2, prof])
    db_session.commit()

    turma_resp = client.post(
        "/api/v1/classes/",
        json={
            "nome": "Turma Mista Ampla",
            "cursos_ids": [curso1.id, curso2.id],
            "sala_id": sala.id,
            "professor_id": prof.id,
            "faixa_etaria": "JUVENIL",
            "dia_semana": "TERCA",
            "turno": "TARDE",
            "horario_inicio": "14:30",
            "horario_fim": "16:30",
            "capacidade_maxima": 12,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert turma_resp.status_code == 201
    turma_id = turma_resp.json()["id"]

    for i in range(10):
        a = Aluno(nome=f"Aluno Amplo {i}", data_nascimento=date(2010, 2, 1), ativo=True)
        db_session.add(a)
        db_session.commit()
        db_session.refresh(a)

        mat_resp = client.post(
            "/api/v1/enrollments/",
            json={
                "aluno_id": a.id,
                "turma_id": turma_id,
                "curso_id": curso2.id if i % 2 == 0 else curso1.id,
                "data_matricula": "2026-11-01",
                "data_inicio": "2026-11-05",
                "valor_mensalidade": 275.0 if i % 2 == 0 else 260.0,
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert mat_resp.status_code == 201
        assert mat_resp.json()["curso_id"] == (curso2.id if i % 2 == 0 else curso1.id)


def deve_excluir_matricula_sem_pagamento_e_bloquear_quando_houver_fatura_paga(
    client, admin_token, turma_fase3, aluno_fase3, db_session
):
    from app.models.financial import Invoice, StatusTitulo

    cria = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": aluno_fase3.id,
            "turma_id": turma_fase3.id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 290.0,
            "quantidade_parcelas": 2,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cria.status_code == 201
    mat_id = cria.json()["id"]

    # Marca uma fatura como PAGO e verifica bloqueio (409)
    inv = db_session.query(Invoice).filter(Invoice.matricula_id == mat_id).first()
    inv.status = StatusTitulo.PAGO.value
    db_session.commit()

    del_block = client.delete(f"/api/v1/enrollments/{mat_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_block.status_code == 409

    # Volta faturas para pendente e exclui com sucesso
    for f in db_session.query(Invoice).filter(Invoice.matricula_id == mat_id).all():
        f.status = StatusTitulo.PENDENTE.value
    db_session.commit()

    del_ok = client.delete(f"/api/v1/enrollments/{mat_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_ok.status_code == 200
    assert "excluída" in del_ok.json()["mensagem"].lower()
    assert client.get(f"/api/v1/enrollments/{mat_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 404
