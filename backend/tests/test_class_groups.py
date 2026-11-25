from datetime import date
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.student import Aluno
from app.models.enrollment import Matricula, StatusMatricula
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.initial_data import aplicar_migracoes, aplicar_correcoes_dados_p0


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
        "cursos_ids": [curso.id],
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


def deve_permitir_turma_com_capacidade_acima_de_9_respeitando_capacidade_da_sala(
    client, admin_token, curso, professor, db_session
):
    sala_ampla = Room(nome="Sala Ampla 14", capacidade=14, ativa=True)
    db_session.add(sala_ampla)
    db_session.commit()
    db_session.refresh(sala_ampla)

    payload_ok = {
        "nome": "Turma Ampla",
        "cursos_ids": [curso.id],
        "sala_id": sala_ampla.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "QUINTA",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "11:00",
        "capacidade_maxima": 14,
    }
    resp_ok = client.post("/api/v1/classes/", json=payload_ok, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_ok.status_code == 201
    assert resp_ok.json()["capacidade_maxima"] == 14

    payload_excede = dict(payload_ok)
    payload_excede["nome"] = "Turma Excede Sala"
    payload_excede["capacidade_maxima"] = 15
    resp_err = client.post("/api/v1/classes/", json=payload_excede, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_err.status_code == 422


def deve_permitir_mesma_sala_e_mesmo_professor_no_mesmo_horario_para_turmas_mistas(
    client, admin_token, sala, curso, professor, db_session
):
    """Remoção do bloqueio de choque de sala e professor para suportar turmas mistas."""
    curso2 = Course(nome="Mangá Testes", valor_mensalidade=260.0, ativo=True)
    db_session.add(curso2)
    db_session.commit()
    db_session.refresh(curso2)

    turma1 = {
        "nome": "Turma Mista Parte 1",
        "cursos_ids": [curso.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SABADO",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "11:00",
        "capacidade_maxima": 9
    }
    r1 = client.post("/api/v1/classes/", json=turma1, headers={"Authorization": f"Bearer {admin_token}"})
    assert r1.status_code == 201

    turma2 = {
        "nome": "Turma Mista Parte 2",
        "cursos_ids": [curso2.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "JUVENIL",
        "dia_semana": "SABADO",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "11:00",
        "capacidade_maxima": 9
    }
    r2 = client.post("/api/v1/classes/", json=turma2, headers={"Authorization": f"Bearer {admin_token}"})
    assert r2.status_code == 201


def deve_associar_multiplos_cursos_na_mesma_turma_e_filtrar_por_curso(
    client, admin_token, sala, curso, professor, db_session
):
    curso2 = Course(nome="Desenho Artístico M2", valor_mensalidade=260.0, ativo=True)
    curso3 = Course(nome="Mangá Misto", valor_mensalidade=260.0, ativo=True)
    db_session.add_all([curso2, curso3])
    db_session.commit()

    payload = {
        "nome": "Turma Mista Terça Tarde",
        "cursos_ids": [curso.id, curso2.id, curso3.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "JUVENIL",
        "dia_semana": "TERCA",
        "turno": "TARDE",
        "horario_inicio": "14:30",
        "horario_fim": "16:30",
        "capacidade_maxima": 9,
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert set(data["cursos_ids"]) == {curso.id, curso2.id, curso3.id}
    assert "Desenho Artístico M2" in data["cursos_nomes"]
    assert "Mangá Misto" in data["cursos_nomes"]

    lista = client.get(f"/api/v1/classes/?curso_id={curso3.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert lista.status_code == 200
    assert any(t["id"] == data["id"] for t in lista.json())


def deve_exigir_selecao_explicita_de_faixa_etaria(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Turma Sem Faixa",
        "cursos_ids": [curso.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "dia_semana": "QUARTA",
        "turno": "TARDE",
        "horario_inicio": "14:00",
        "horario_fim": "16:00",
        "capacidade_maxima": 9,
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_editar_e_excluir_turma(client, admin_token, sala, curso, professor, db_session):
    sala2 = Room(nome="Sala 3 Destino", capacidade=12, ativa=True)
    curso2 = Course(nome="Curso Extra Edit", valor_mensalidade=280.0, ativo=True)
    db_session.add_all([sala2, curso2])
    db_session.commit()

    cria = client.post(
        "/api/v1/classes/",
        json={
            "nome": "Turma Editável",
            "cursos_ids": [curso.id],
            "sala_id": sala.id,
            "professor_id": professor.id,
            "faixa_etaria": "ADULTO",
            "dia_semana": "SEXTA",
            "turno": "TARDE",
            "horario_inicio": "14:00",
            "horario_fim": "16:00",
            "capacidade_maxima": 9,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cria.status_code == 201
    turma_id = cria.json()["id"]

    upd = client.put(
        f"/api/v1/classes/{turma_id}",
        json={
            "nome": "Turma Editada Mista",
            "cursos_ids": [curso.id, curso2.id],
            "sala_id": sala2.id,
            "capacidade_maxima": 12,
            "faixa_etaria": "JUVENIL",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upd.status_code == 200
    assert upd.json()["nome"] == "Turma Editada Mista"
    assert upd.json()["capacidade_maxima"] == 12
    assert set(upd.json()["cursos_ids"]) == {curso.id, curso2.id}

    # Sem vínculos: deve excluir fisicamente
    del_resp = client.delete(f"/api/v1/classes/{turma_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_resp.status_code == 200
    assert "excluída" in del_resp.json()["mensagem"].lower()

    get_after = client.get(f"/api/v1/classes/{turma_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_after.status_code == 404


def deve_desativar_turma_quando_possuir_matriculas_vinculadas(
    client, admin_token, sala, curso, professor, db_session
):
    cria = client.post(
        "/api/v1/classes/",
        json={
            "nome": "Turma Com Matrícula",
            "cursos_ids": [curso.id],
            "sala_id": sala.id,
            "professor_id": professor.id,
            "faixa_etaria": "ADULTO",
            "dia_semana": "SEGUNDA",
            "turno": "MANHA",
            "horario_inicio": "09:00",
            "horario_fim": "11:00",
            "capacidade_maxima": 9,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    turma_id = cria.json()["id"]

    aluno = Aluno(nome="Aluno Vínculo Turma", data_nascimento=date(1995, 5, 10), ativo=True)
    db_session.add(aluno)
    db_session.commit()

    mat = Matricula(
        aluno_id=aluno.id,
        turma_id=turma_id,
        status=StatusMatricula.ATIVA.value,
        data_matricula=date(2026, 11, 1),
        data_inicio=date(2026, 11, 5),
        valor_mensalidade=260.0,
    )
    db_session.add(mat)
    db_session.commit()

    del_resp = client.delete(f"/api/v1/classes/{turma_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_resp.status_code == 200
    assert "desativada" in del_resp.json()["mensagem"].lower()

    get_after = client.get(f"/api/v1/classes/{turma_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_after.status_code == 200
    assert get_after.json()["ativa"] is False


def deve_validar_classificacao_etaria_infantil(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Desenho Infantil Manhã",
        "cursos_ids": [curso.id],
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
        "cursos_ids": [curso.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SEGUNDA",
        "turno": "MANHA",
        "horario_inicio": "25:00",
        "horario_fim": "27:00",
        "capacidade_maxima": 9
    }
    resp = client.post("/api/v1/classes/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_rejeitar_horario_inicio_maior_que_fim(client, admin_token, sala, curso, professor):
    payload = {
        "nome": "Turma Invertida",
        "cursos_ids": [curso.id],
        "sala_id": sala.id,
        "professor_id": professor.id,
        "faixa_etaria": "ADULTO",
        "dia_semana": "SEGUNDA",
        "turno": "MANHA",
        "horario_inicio": "11:00",
        "horario_fim": "09:00",
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


def deve_migrar_schema_legado_e_aplicar_correcoes_dados_p0(tmp_path):
    db_file = tmp_path / "legado.db"
    eng = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    with eng.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY, nome VARCHAR(100) NOT NULL UNIQUE,
                descricao TEXT, duracao_meses INTEGER, valor_mensalidade FLOAT NOT NULL,
                ativo BOOLEAN NOT NULL, criado_em DATETIME NOT NULL
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE teachers (
                id INTEGER PRIMARY KEY, nome VARCHAR(120) NOT NULL, email VARCHAR(120) NOT NULL UNIQUE,
                telefone VARCHAR(30), endereco VARCHAR(255), especialidades VARCHAR(255),
                disponibilidade VARCHAR(255), substituto_id INTEGER, user_id INTEGER,
                ativo BOOLEAN NOT NULL, criado_em DATETIME NOT NULL
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE rooms (
                id INTEGER PRIMARY KEY, nome VARCHAR(50) NOT NULL UNIQUE,
                capacidade INTEGER NOT NULL, descricao VARCHAR(255),
                ativa BOOLEAN NOT NULL, criada_em DATETIME NOT NULL,
                CONSTRAINT check_capacidade_maxima_9 CHECK (capacidade <= 9),
                CONSTRAINT check_capacidade_minima_1 CHECK (capacidade >= 1)
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE class_groups (
                id INTEGER PRIMARY KEY, nome VARCHAR(100) NOT NULL,
                curso_id INTEGER NOT NULL, sala_id INTEGER NOT NULL, professor_id INTEGER NOT NULL,
                faixa_etaria VARCHAR(30) NOT NULL, dia_semana VARCHAR(20) NOT NULL,
                turno VARCHAR(20) NOT NULL, horario_inicio VARCHAR(5) NOT NULL,
                horario_fim VARCHAR(5) NOT NULL, capacidade_maxima INTEGER NOT NULL,
                ativa BOOLEAN NOT NULL, criada_em DATETIME NOT NULL,
                CONSTRAINT check_turma_capacidade_maxima_9 CHECK (capacidade_maxima <= 9),
                CONSTRAINT check_turma_capacidade_minima_1 CHECK (capacidade_maxima >= 1)
            )
        """)
        conn.exec_driver_sql("INSERT INTO courses VALUES (1, 'Desenho Artístico', NULL, 12, 260, 1, '2026-11-01')")
        conn.exec_driver_sql("INSERT INTO courses VALUES (2, 'Aquarela', NULL, 12, 260, 1, '2026-11-01')")
        conn.exec_driver_sql("INSERT INTO teachers (id, nome, email, ativo, criado_em) VALUES (1, 'Ana Júlia', 'ana@hb.com', 1, '2026-11-01')")
        conn.exec_driver_sql("INSERT INTO teachers (id, nome, email, ativo, criado_em) VALUES (2, 'Helena', 'helena@hb.com', 1, '2026-11-01')")
        conn.exec_driver_sql("INSERT INTO rooms VALUES (1, 'Sala 1', 9, NULL, 1, '2026-11-01')")
        conn.exec_driver_sql("INSERT INTO rooms VALUES (3, 'Sala 3', 9, NULL, 1, '2026-11-01')")
        conn.exec_driver_sql("""
            INSERT INTO class_groups VALUES
            (1, 'Desenho Artístico módulo 1 - Ana Júlia - Terça 14:30', 1, 1, 1, 'INFANTIL', 'TERCA', 'TARDE', '14:30', '16:30', 9, 1, '2026-11-01'),
            (2, 'Pintura em Aquarela - Helena - Quarta 14:00', 2, 2, 2, 'INFANTIL', 'QUARTA', 'TARDE', '14:00', '16:00', 9, 1, '2026-11-01')
        """)

    Base.metadata.create_all(bind=eng)
    aplicar_migracoes(eng)

    SessionTest = sessionmaker(bind=eng)
    db = SessionTest()
    try:
        aplicar_correcoes_dados_p0(db)
        ana = db.query(ClassGroup).filter(ClassGroup.id == 1).first()
        helena = db.query(ClassGroup).filter(ClassGroup.id == 2).first()
        assert ana.sala_id == 3
        assert ana.faixa_etaria is None
        assert helena.faixa_etaria is None

        # Deve permitir capacidade > 9 após migração
        sala_1 = db.query(Room).filter(Room.id == 1).first()
        sala_1.capacidade = 16
        db.commit()

        # Idempotência: se usuário definir faixa etária manualmente depois, nova execução não sobrescreve
        helena.faixa_etaria = "ADULTO"
        db.commit()
        aplicar_correcoes_dados_p0(db)
        db.refresh(helena)
        assert helena.faixa_etaria == "ADULTO"
    finally:
        db.close()
        eng.dispose()
