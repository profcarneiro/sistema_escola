from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.core.security import get_password_hash


# ─────────────────────────────────────────────
# SALAS
# ─────────────────────────────────────────────

def deve_listar_salas_ativas(client, admin_token, db_session):
    # Seed de sala
    sala = Room(nome="Sala 1", capacidade=9, ativa=True)
    db_session.add(sala)
    db_session.commit()

    resp = client.get("/api/v1/rooms/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(s["ativa"] is True for s in data)


def deve_criar_sala_com_capacidade_valida(client, admin_token):
    resp = client.post(
        "/api/v1/rooms/",
        json={"nome": "Estúdio Aquarela", "capacidade": 9},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Estúdio Aquarela"
    assert data["capacidade"] == 9


def deve_permitir_sala_com_capacidade_maior_que_9_e_configuravel(client, admin_token):
    resp = client.post(
        "/api/v1/rooms/",
        json={"nome": "Sala Grande", "capacidade": 15},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["capacidade"] == 15

    upd = client.put(
        f"/api/v1/rooms/{data['id']}",
        json={"capacidade": 20},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upd.status_code == 200
    assert upd.json()["capacidade"] == 20


def deve_rejeitar_sala_com_capacidade_zero(client, admin_token):
    resp = client.post(
        "/api/v1/rooms/",
        json={"nome": "Sala Vazia", "capacidade": 0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422


def deve_rejeitar_sala_duplicada(client, admin_token, db_session):
    sala = Room(nome="Sala Única", capacidade=9, ativa=True)
    db_session.add(sala)
    db_session.commit()

    resp = client.post(
        "/api/v1/rooms/",
        json={"nome": "Sala Única", "capacidade": 8},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400


def deve_bloquear_criacao_de_sala_por_professor(client, professor_token):
    resp = client.post(
        "/api/v1/rooms/",
        json={"nome": "Sala do Professor", "capacidade": 9},
        headers={"Authorization": f"Bearer {professor_token}"}
    )
    assert resp.status_code == 403


def deve_obter_sala_por_id(client, admin_token, db_session):
    sala = Room(nome="Sala Busca ID", capacidade=7, ativa=True)
    db_session.add(sala)
    db_session.commit()
    db_session.refresh(sala)

    resp = client.get(f"/api/v1/rooms/{sala.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Sala Busca ID"


def deve_retornar_404_para_sala_inexistente(client, admin_token):
    resp = client.get("/api/v1/rooms/99999", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404


def deve_excluir_sala_livre_e_desativar_sala_com_turma(client, admin_token, db_session):
    from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno

    cria = client.post(
        "/api/v1/rooms/",
        json={"nome": "Sala Temporária Del", "capacidade": 12},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cria.status_code == 201
    sala_livre_id = cria.json()["id"]

    del_livre = client.delete(f"/api/v1/rooms/{sala_livre_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_livre.status_code == 200
    assert "excluída" in del_livre.json()["mensagem"].lower()
    assert client.get(f"/api/v1/rooms/{sala_livre_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 404

    sala_vinc = Room(nome="Sala Com Turma Del", capacidade=10, ativa=True)
    curso = Course(nome="Curso Sala Del", valor_mensalidade=250.0, ativo=True)
    prof = Teacher(nome="Prof Sala Del", email="prof.sala.del@hbartes.com", ativo=True)
    db_session.add_all([sala_vinc, curso, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Turma Sala Del",
        curso_id=curso.id,
        sala_id=sala_vinc.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.QUARTA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=10,
        ativa=True,
    )
    db_session.add(turma)
    db_session.commit()

    del_vinc = client.delete(f"/api/v1/rooms/{sala_vinc.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_vinc.status_code == 200
    assert "desativada" in del_vinc.json()["mensagem"].lower()
    get_vinc = client.get(f"/api/v1/rooms/{sala_vinc.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_vinc.status_code == 200
    assert get_vinc.json()["ativa"] is False
