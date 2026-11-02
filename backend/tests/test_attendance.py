import pytest
from datetime import date
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.models.student import Aluno
from app.models.enrollment import Matricula, StatusMatricula


@pytest.fixture
def ambiente_fase4(db_session):
    sala = Room(nome="Sala Pintura F4", capacidade=9, ativa=True)
    curso = Course(nome="Aquarela F4", valor_mensalidade=260.0, ativo=True)
    prof = Teacher(nome="Prof Helena Pintura", email="helena.pintura@hbartes.com", ativo=True)
    db_session.add_all([sala, curso, prof])
    db_session.commit()

    turma_origem = ClassGroup(
        nome="Aquarela Terça Tarde F4",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.TERCA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=9,
        ativa=True
    )
    turma_destino = ClassGroup(
        nome="Aquarela Quinta Manhã F4",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.QUINTA.value,
        turno=Turno.MANHA.value,
        horario_inicio="09:00",
        horario_fim="11:00",
        capacidade_maxima=9,
        ativa=True
    )
    db_session.add_all([turma_origem, turma_destino])
    db_session.commit()

    aluno = Aluno(
        nome="Ana Paula Arte",
        data_nascimento=date(1993, 7, 22),
        cpf="111.999.888-22",
        ativo=True
    )
    db_session.add(aluno)
    db_session.commit()

    matricula = Matricula(
        aluno_id=aluno.id,
        turma_id=turma_origem.id,
        status=StatusMatricula.ATIVA.value,
        data_matricula=date(2026, 11, 1),
        data_inicio=date(2026, 11, 3),
        valor_mensalidade=260.0,
        numero_contrato="MAT-202611-TESTE01"
    )
    db_session.add(matricula)
    db_session.commit()

    return {
        "turma_origem": turma_origem,
        "turma_destino": turma_destino,
        "professor": prof,
        "aluno": aluno,
        "matricula": matricula
    }


def deve_registrar_aula_no_diario_de_classe(client, admin_token, ambiente_fase4):
    payload = {
        "turma_id": ambiente_fase4["turma_origem"].id,
        "professor_id": ambiente_fase4["professor"].id,
        "data_aula": "2026-11-10",
        "tema_aula": "Técnica de Aguada e Degradê em Aquarela",
        "conteudo_programatico": "Introdução aos pigmentos transparentes, tensão superficial da água.",
        "materiais_utilizados": "Papel Arches 300g, pincel redondo nº 8, pastilhas Winsor & Newton.",
        "observacoes": "Turma com excelente rendimento inicial."
    }
    resp = client.post("/api/v1/attendance/lessons", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["tema_aula"] == "Técnica de Aguada e Degradê em Aquarela"
    assert data["turma_nome"] == ambiente_fase4["turma_origem"].nome


def deve_registrar_chamada_com_presentes_e_faltas(client, admin_token, ambiente_fase4):
    # Cria aula primeiro
    aula_resp = client.post(
        "/api/v1/attendance/lessons",
        json={
            "turma_id": ambiente_fase4["turma_origem"].id,
            "professor_id": ambiente_fase4["professor"].id,
            "data_aula": "2026-11-10",
            "tema_aula": "Estudo de Luz e Sombra"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    lesson_id = aula_resp.json()["id"]

    # Registra presença e falta
    payload_batch = {
        "frequencias": [
            {
                "aluno_id": ambiente_fase4["aluno"].id,
                "matricula_id": ambiente_fase4["matricula"].id,
                "status": "FALTA",
                "motivo_justificativa": "Consulta médica agendada"
            }
        ]
    }
    resp = client.post(
        f"/api/v1/attendance/lessons/{lesson_id}/batch",
        json=payload_batch,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    lista = resp.json()
    assert len(lista) == 1
    assert lista[0]["status"] == "FALTA"
    assert lista[0]["motivo_justificativa"] == "Consulta médica agendada"


def deve_permitir_reposicao_dentro_do_mesmo_mes(client, admin_token, ambiente_fase4):
    """
    REGRA DO BRIEFING: Reposição dentro do próprio mês da falta → DEVE SER ACEITA.
    Falta em 10/11/2026 → Reposição em 26/11/2026.
    """
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "matricula_origem_id": ambiente_fase4["matricula"].id,
        "data_falta": "2026-11-10",
        "turma_destino_id": ambiente_fase4["turma_destino"].id,
        "data_reposicao": "2026-11-26",
        "observacoes": "Reposição de aula no mesmo mês"
    }
    resp = client.post("/api/v1/attendance/makeups", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "AGENDADA"
    assert data["data_falta"] == "2026-11-10"
    assert data["data_reposicao"] == "2026-11-26"


def deve_permitir_reposicao_na_primeira_semana_do_mes_seguinte(client, admin_token, ambiente_fase4):
    """
    REGRA DO BRIEFING: Reposição na 1ª semana do mês seguinte (até dia 07) → DEVE SER ACEITA.
    Falta em 24/11/2026 → Reposição em 03/12/2026 (dia <= 7).
    """
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "matricula_origem_id": ambiente_fase4["matricula"].id,
        "data_falta": "2026-11-24",
        "turma_destino_id": ambiente_fase4["turma_destino"].id,
        "data_reposicao": "2026-12-03",  # 1ª semana de dezembro (dia 3 <= 7)
        "observacoes": "Reposição na primeira semana de dezembro"
    }
    resp = client.post("/api/v1/attendance/makeups", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "AGENDADA"
    assert data["data_reposicao"] == "2026-12-03"


def deve_rejeitar_reposicao_apos_a_primeira_semana_do_mes_seguinte(client, admin_token, ambiente_fase4):
    """
    REGRA DO BRIEFING: Reposição no mês seguinte APÓS o 7º dia → DEVE SER REJEITADA.
    Falta em 24/11/2026 → Reposição em 15/12/2026 (dia 15 > 7) → ERRO 422.
    """
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "matricula_origem_id": ambiente_fase4["matricula"].id,
        "data_falta": "2026-11-24",
        "turma_destino_id": ambiente_fase4["turma_destino"].id,
        "data_reposicao": "2026-12-15",  # Passou da 1ª semana!
        "observacoes": "Reposição tardia inválida"
    }
    resp = client.post("/api/v1/attendance/makeups", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422
    assert "primeira semana" in resp.text.lower() or "fora do prazo" in resp.text.lower()


def deve_rejeitar_reposicao_dois_meses_depois(client, admin_token, ambiente_fase4):
    """
    REGRA DO BRIEFING: Reposição 2 meses após a falta → DEVE SER REJEITADA.
    Falta em 10/10/2026 → Reposição em 15/12/2026 → ERRO 422.
    """
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "matricula_origem_id": ambiente_fase4["matricula"].id,
        "data_falta": "2026-10-10",
        "turma_destino_id": ambiente_fase4["turma_destino"].id,
        "data_reposicao": "2026-12-10",
        "observacoes": "Reposição muito atrasada"
    }
    resp = client.post("/api/v1/attendance/makeups", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422
    assert "fora do prazo" in resp.text.lower()


def deve_rejeitar_reposicao_com_data_anterior_a_falta(client, admin_token, ambiente_fase4):
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "matricula_origem_id": ambiente_fase4["matricula"].id,
        "data_falta": "2026-11-20",
        "turma_destino_id": ambiente_fase4["turma_destino"].id,
        "data_reposicao": "2026-11-10",  # Anterior à falta
        "observacoes": "Data invertida"
    }
    resp = client.post("/api/v1/attendance/makeups", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422


def deve_cadastrar_avaliacao_e_relatorio_de_portfolio(client, admin_token, ambiente_fase4):
    payload = {
        "aluno_id": ambiente_fase4["aluno"].id,
        "turma_id": ambiente_fase4["turma_origem"].id,
        "professor_id": ambiente_fase4["professor"].id,
        "periodo": "2º Semestre 2026",
        "data_avaliacao": "2026-11-30",
        "conceito": "EXCELENTE",
        "nota": 9.5,
        "relatorio_descritivo": (
            "A aluna demonstrou excelente domínio das técnicas de aguada e pinceladas expressivas. "
            "Seu portfólio inclui 4 obras concluídas com ótima harmonia cromática e controle de água."
        )
    }
    resp = client.post("/api/v1/attendance/evaluations", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["conceito"] == "EXCELENTE"
    assert data["nota"] == 9.5
    assert "harmonia cromática" in data["relatorio_descritivo"]


def deve_consultar_portfolio_do_aluno(client, admin_token, ambiente_fase4):
    aluno_id = ambiente_fase4["aluno"].id
    # Cadastra uma avaliação
    client.post(
        "/api/v1/attendance/evaluations",
        json={
            "aluno_id": aluno_id,
            "turma_id": ambiente_fase4["turma_origem"].id,
            "professor_id": ambiente_fase4["professor"].id,
            "periodo": "Módulo Básico 2026",
            "data_avaliacao": "2026-11-15",
            "conceito": "BOM",
            "relatorio_descritivo": "Bom progresso nos estudos de proporção e anatomia artística."
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    resp = client.get(f"/api/v1/attendance/evaluations/student/{aluno_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    lista = resp.json()
    assert len(lista) >= 1
    assert lista[0]["aluno_nome"] == ambiente_fase4["aluno"].nome
