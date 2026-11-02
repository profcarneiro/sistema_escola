import pytest
from datetime import date
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.models.student import Aluno
from app.models.guardian import Responsavel
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Invoice, StatusTitulo


@pytest.fixture
def ambiente_fase6(db_session):
    sala = Room(nome="Sala Central F6", capacidade=9, ativa=True)
    curso = Course(nome="Aquarela F6", valor_mensalidade=280.0, ativo=True)
    prof = Teacher(nome="Prof Helena F6", email="helena.f6@hbartes.com", ativo=True)
    db_session.add_all([sala, curso, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Aquarela Sábado Manhã F6",
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

    aluno = Aluno(
        nome="Mariana Barufaldi",
        data_nascimento=date(2010, 4, 15),  # Menor de idade
        telefone="(19) 98888-1111",
        email="mariana@exemplo.com",
        autorizacao_imagem=True,
        ativo=True
    )
    db_session.add(aluno)
    db_session.commit()

    resp = Responsavel(
        aluno_id=aluno.id,
        nome="Renata Barufaldi (Mãe)",
        cpf="222.333.444-55",
        telefone="(19) 99777-2222",
        email="renata@exemplo.com",
        endereco="Centro, Nova Odessa/SP",
        responsavel_financeiro=True
    )
    db_session.add(resp)
    db_session.commit()

    matricula = Matricula(
        aluno_id=aluno.id,
        turma_id=turma.id,
        status=StatusMatricula.ATIVA.value,
        data_matricula=date(2026, 11, 1),
        data_inicio=date(2026, 11, 7),
        valor_mensalidade=280.0,
        numero_contrato="MAT-202611-F601"
    )
    db_session.add(matricula)
    db_session.commit()

    fatura = Invoice(
        matricula_id=matricula.id,
        aluno_id=aluno.id,
        responsavel_id=resp.id,
        descricao="Mensalidade 11/2026",
        competencia="2026-11",
        valor_nominal=280.0,
        desconto_aplicado=0.0,
        valor_final=280.0,
        data_vencimento=date(2026, 11, 10),
        status=StatusTitulo.PENDENTE.value
    )
    db_session.add(fatura)
    db_session.commit()

    return {
        "turma": turma,
        "aluno": aluno,
        "responsavel": resp,
        "matricula": matricula,
        "fatura": fatura
    }


def deve_gerar_link_whatsapp_de_cobranca(client, admin_token, ambiente_fase6):
    fat_id = ambiente_fase6["fatura"].id
    resp = client.post(
        f"/api/v1/communication/whatsapp-invoice-reminder/{fat_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "https://wa.me/" in data["whatsapp_url"]
    assert "5519997772222" in data["whatsapp_url"]  # Telefone higienizado com DDI 55
    assert "Mariana Barufaldi" in data["mensagem"]
    assert "280.00" in data["mensagem"]


def deve_gerar_link_whatsapp_de_confirmacao_de_matricula(client, admin_token, ambiente_fase6):
    mat_id = ambiente_fase6["matricula"].id
    resp = client.post(
        f"/api/v1/communication/whatsapp-enrollment-welcome/{mat_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "https://wa.me/" in data["whatsapp_url"]
    assert "Seja muito bem-vindo" in data["mensagem"]
    assert "Aquarela Sábado Manhã F6" in data["mensagem"]


def deve_gerar_link_whatsapp_personalizado(client, admin_token):
    payload = {
        "destinatario_nome": "Jorge Aluno",
        "telefone": "(19) 98123-4567",
        "mensagem": "Olá Jorge, seu certificado de conclusão já está disponível no atelier!"
    }
    resp = client.post(
        "/api/v1/communication/whatsapp-custom-link",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert "https://wa.me/5519981234567" in resp.json()["whatsapp_url"]


def deve_obter_dados_do_dashboard_gerencial(client, admin_token, ambiente_fase6):
    resp = client.get("/api/v1/reports/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_alunos_ativos"] >= 1
    assert data["total_turmas_ativas"] >= 1
    assert "taxa_ocupacao_geral_percentual" in data


def deve_obter_relatorio_de_ocupacao_de_salas(client, admin_token, ambiente_fase6):
    resp = client.get("/api/v1/reports/room-occupancy", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    salas = resp.json()
    assert len(salas) >= 1
    assert all(s["capacidade_sala"] <= 9 for s in salas)  # Teto inegociável de 9


def deve_exportar_cadastro_de_alunos_em_csv(client, admin_token, ambiente_fase6):
    resp = client.get("/api/v1/reports/export/students-csv", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    texto = resp.text
    assert "Mariana Barufaldi" in texto
    assert "Renata Barufaldi" in texto


def deve_exportar_titulos_financeiros_em_csv(client, admin_token, ambiente_fase6):
    resp = client.get("/api/v1/reports/export/invoices-csv", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    texto = resp.text
    assert "Mensalidade 11/2026" in texto
    assert "280.00" in texto


def deve_criar_e_listar_backup_do_banco_de_dados(client, admin_token):
    # Cria backup
    cria = client.post("/api/v1/backup/create", headers={"Authorization": f"Bearer {admin_token}"})
    assert cria.status_code == 201
    backup_info = cria.json()
    assert backup_info["arquivo"].startswith("escola_artes_backup_")
    assert backup_info["tamanho_bytes"] > 0

    # Lista backups
    lista = client.get("/api/v1/backup/list", headers={"Authorization": f"Bearer {admin_token}"})
    assert lista.status_code == 200
    itens = lista.json()
    assert len(itens) >= 1
    assert any(b["arquivo"] == backup_info["arquivo"] for b in itens)
