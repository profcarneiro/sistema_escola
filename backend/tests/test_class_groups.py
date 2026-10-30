import pytest
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno


# ─── Fixtures auxiliares para Fase 2 ─────────────────────────────────────────

@pytest.fixture
def sala(db_session):
    s = Room(nome="Sala Testes Turmas", capacidade=9, ativa=True)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def curso(db_session):
    c = Course(nome="Aquarela Testes", valor_mensalidade=260.0, ativo=True)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def professor(db_session):
    p = Teacher(nome="Prof Turmas Teste", email="turmas.teste@hbartes.com", ativo=True)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def turma_payload(sala, curso, professor):
    return {
        "nome": "Aquarela Terça Tarde",
        "curso_id": curso.id,
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "TERCA",
        "turno": "TARDE",
        "horario_inicio": "14:00",
        "horario_fim": "16:00",
        "capacidade_maxima": 9
    }


# ─── Testes de Turmas ─────────────────────────────────────────────────────────

def deve_criar_turma_com_todos_os_campos(client, admin_token, turma_payload):
    resp = client.post(
        "/api/v1/classes/",
        json=turma_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Aquarela Terça Tarde"
    assert data["capacidade_maxima"] == 9
    assert data["faixa_etaria"] == "ADULTO"
    assert data["dia_semana"] == "TERCA"
    assert data["ativa"] is True


def deve_rejeitar_turma_com_capacidade_acima_de_9(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Turma Lotada",
        "curso_id": curso.id,
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "QUINTA",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "11:00",
        "capacidade_maxima": 10  # ← INVÁLIDO
    }
    resp = client.post(
        "/api/v1/classes/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422


def deve_detectar_conflito_de_sala(client, admin_token, sala, curso, professor, db_session):
    """Dois turmas no mesmo dia, sala e horário sobreposto devem ser rejeitadas."""
    # Cria primeira turma diretamente no banco
    turma_existente = ClassGroup(
        nome="Turma Existente",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=professor.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.SABADO.value,
        turno=Turno.MANHA.value,
        horario_inicio="09:00",
        horario_fim="11:00",
        capacidade_maxima=9,
        ativa=True
    )
    db_session.add(turma_existente)
    db_session.commit()

    # Cria segundo professor para o conflito ser apenas de sala
    prof2 = Teacher(nome="Prof Conflito Sala", email="conflito.sala@hbartes.com", ativo=True)
    db_session.add(prof2)
    db_session.commit()
    db_session.refresh(prof2)

    # Tenta criar turma na mesma sala e horário sobreposto
    payload_conflito = {
        "nome": "Turma Conflitante",
        "curso_id": curso.id,
        "sala_id": sala.id,  # mesma sala ← CONFLITO
        "professor_id": prof2.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SABADO",
        "turno": "MANHA",
        "horario_inicio": "10:00",  # sobrepõe 09:00-11:00
        "horario_fim": "12:00",
        "capacidade_maxima": 9
    }
    resp = client.post(
        "/api/v1/classes/",
        json=payload_conflito,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409
    assert "Conflito de sala" in resp.json()["detail"]


def deve_detectar_conflito_de_professor(client, admin_token, sala, curso, professor, db_session):
    """Mesmo professor alocado em dois horários sobrepostos no mesmo dia deve ser rejeitado."""
    sala2 = Room(nome="Sala Extra Conflito Prof", capacidade=9, ativa=True)
    db_session.add(sala2)
    db_session.commit()
    db_session.refresh(sala2)

    turma_existente = ClassGroup(
        nome="Turma Prof Existente",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=professor.id,
        faixa_etaria=FaixaEtaria.JUVENIL.value,
        dia_semana=DiaSemana.TERCA.value,
        turno=Turno.NOITE.value,
        horario_inicio="19:00",
        horario_fim="21:00",
        capacidade_maxima=9,
        ativa=True
    )
    db_session.add(turma_existente)
    db_session.commit()

    payload_conflito = {
        "nome": "Turma Conflita Professor",
        "curso_id": curso.id,
        "sala_id": sala2.id,  # sala diferente
        "professor_id": professor.id,  # mesmo professor ← CONFLITO
        "faixa_etaria": "ADULTO",
        "dia_semana": "TERCA",
        "turno": "NOITE",
        "horario_inicio": "20:00",  # sobrepõe 19:00-21:00
        "horario_fim": "22:00",
        "capacidade_maxima": 9
    }
    resp = client.post(
        "/api/v1/classes/",
        json=payload_conflito,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409
    assert "Conflito de professor" in resp.json()["detail"]


def deve_permitir_turmas_em_dias_diferentes_sem_conflito(client, admin_token, sala, curso, professor, turma_payload):
    """Mesmo professor e sala em dias distintos não geram conflito."""
    # Cria primeira turma
    resp1 = client.post("/api/v1/classes/", json=turma_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp1.status_code == 201

    # Cria segunda turma em dia diferente
    payload2 = dict(turma_payload)
    payload2["nome"] = "Aquarela Quinta Manhã"
    payload2["dia_semana"] = "QUINTA"
    payload2["turno"] = "MANHA"
    payload2["horario_inicio"] = "09:00"
    payload2["horario_fim"] = "11:00"

    resp2 = client.post("/api/v1/classes/", json=payload2, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp2.status_code == 201


def deve_validar_classificacao_etaria_infantil(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Desenho Infantil Manhã",
        "curso_id": curso.id,
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "INFANTIL",
        "dia_semana": "SABADO",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "10:30",
        "capacidade_maxima": 9
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    assert resp.json()["faixa_etaria"] == "INFANTIL"


def deve_rejeitar_horario_invalido(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Turma Horário Inválido",
        "curso_id": curso.id,
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SEGUNDA",
        "turno": "MANHA",
        "horario_inicio": "25:00",  # inválido
        "horario_fim": "27:00",
        "capacidade_maxima": 9
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_rejeitar_horario_inicio_maior_que_fim(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Turma Invertida",
        "curso_id": curso.id,
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SEGUNDA",
        "turno": "MANHA",
        "horario_inicio": "11:00",
        "horario_fim": "09:00",  # início após fim ← inválido
        "capacidade_maxima": 9
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_listar_turmas_com_filtro_por_dia(client, admin_token, turma_payload):
    client.post("/api/v1/classes/", json=turma_payload, headers={"Authorization": f"Bearer {admin_token}"})

    resp = client.get("/api/v1/classes/?dia_semana=TERCA", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    turmas = resp.json()
    assert all(t["dia_semana"] == "TERCA" for t in turmas)
