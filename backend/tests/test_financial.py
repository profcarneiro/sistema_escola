import pytest
from datetime import date, timedelta
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.models.student import Aluno
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Invoice, StatusTitulo, FormaPagamento


@pytest.fixture
def ambiente_fase5(db_session):
    sala = Room(nome="Sala Financeiro F5", capacidade=9, ativa=True)
    curso = Course(nome="Mangá F5", valor_mensalidade=260.0, ativo=True)
    prof = Teacher(nome="Prof Mangá Financeiro", email="prof.manga@hbartes.com", ativo=True)
    db_session.add_all([sala, curso, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Mangá Sábado Tarde F5",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.JUVENIL.value,
        dia_semana=DiaSemana.SABADO.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=9,
        ativa=True
    )
    db_session.add(turma)
    db_session.commit()

    aluno = Aluno(
        nome="Carlos Eduardo (Mangá)",
        data_nascimento=date(2009, 8, 14),
        cpf="111.444.777-99",
        ativo=True
    )
    db_session.add(aluno)
    db_session.commit()

    matricula = Matricula(
        aluno_id=aluno.id,
        turma_id=turma.id,
        status=StatusMatricula.ATIVA.value,
        data_matricula=date(2026, 11, 1),
        data_inicio=date(2026, 11, 7),
        valor_mensalidade=260.0,
        desconto_percentual=10.0,  # 10% de desconto
        tipo_desconto="irmao",
        numero_contrato="MAT-202611-FIN01"
    )
    db_session.add(matricula)
    db_session.commit()

    return {
        "turma": turma,
        "aluno": aluno,
        "matricula": matricula
    }


def deve_aceitar_pagamento_via_pix(client, admin_token, ambiente_fase5):
    # Cria fatura
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade 11/2026 - PIX",
            "competencia": "2026-11",
            "valor_nominal": 260.0,
            "desconto_aplicado": 26.0,
            "data_vencimento": "2026-11-10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]

    # Paga com PIX
    resp = client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 234.0, "forma_pagamento": "PIX", "comprovante_transacao": "E123456789PIX"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAGO"
    assert resp.json()["forma_pagamento"] == "PIX"


def deve_aceitar_pagamento_via_cartao(client, admin_token, ambiente_fase5):
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade 11/2026 - Cartão",
            "competencia": "2026-11",
            "valor_nominal": 260.0,
            "desconto_aplicado": 0.0,
            "data_vencimento": "2026-11-10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]

    resp = client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 260.0, "forma_pagamento": "CARTAO", "comprovante_transacao": "AUTH-987654"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAGO"
    assert resp.json()["forma_pagamento"] == "CARTAO"


def deve_aceitar_pagamento_via_boleto(client, admin_token, ambiente_fase5):
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade 11/2026 - Boleto",
            "competencia": "2026-11",
            "valor_nominal": 260.0,
            "desconto_aplicado": 0.0,
            "data_vencimento": "2026-11-10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]

    resp = client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 260.0, "forma_pagamento": "BOLETO", "comprovante_transacao": "34191.79001"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAGO"
    assert resp.json()["forma_pagamento"] == "BOLETO"


def deve_aceitar_pagamento_via_dinheiro(client, admin_token, ambiente_fase5):
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade 11/2026 - Dinheiro",
            "competencia": "2026-11",
            "valor_nominal": 260.0,
            "desconto_aplicado": 0.0,
            "data_vencimento": "2026-11-10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]

    resp = client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 260.0, "forma_pagamento": "DINHEIRO", "observacoes": "Recebido na recepção"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAGO"
    assert resp.json()["forma_pagamento"] == "DINHEIRO"


def deve_rejeitar_forma_de_pagamento_fora_do_escopo(client, admin_token, ambiente_fase5):
    """
    REGRA CRÍTICA DO BRIEFING:
    Apenas PIX, CARTAO, BOLETO, DINHEIRO são aceitos.
    Qualquer outra forma deve ser rejeitada.
    """
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade Teste Invalido",
            "competencia": "2026-11",
            "valor_nominal": 260.0,
            "desconto_aplicado": 0.0,
            "data_vencimento": "2026-11-10"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]

    resp = client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 260.0, "forma_pagamento": "CHEQUE"},  # Fora do escopo!
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422


def deve_gerar_lote_mensal_respeitando_descontos(client, admin_token, ambiente_fase5):
    resp = client.post(
        "/api/v1/financial/invoices/generate-monthly?competencia=2026-12&dia_vencimento=10",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    faturas = resp.json()
    assert len(faturas) >= 1
    # Verifica que aluno com 10% de desconto teve desconto aplicado
    fat_aluno = next(f for f in faturas if f["aluno_id"] == ambiente_fase5["aluno"].id)
    assert fat_aluno["valor_nominal"] == 260.0
    assert fat_aluno["desconto_aplicado"] == 26.0
    assert fat_aluno["valor_final"] == 234.0


def deve_identificar_inadimplentes_e_calcular_multa_e_juros(client, admin_token, ambiente_fase5, db_session):
    # Cria fatura vencida há 15 dias
    data_passada = date.today() - timedelta(days=15)
    fatura_atrasada = Invoice(
        matricula_id=ambiente_fase5["matricula"].id,
        aluno_id=ambiente_fase5["aluno"].id,
        descricao="Mensalidade Vencida Teste",
        competencia="2026-10",
        valor_nominal=300.0,
        desconto_aplicado=0.0,
        valor_final=300.0,
        data_vencimento=data_passada,
        status=StatusTitulo.PENDENTE.value
    )
    db_session.add(fatura_atrasada)
    db_session.commit()

    # Consulta régua de cobrança de inadimplentes
    resp = client.get("/api/v1/financial/defaulters", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    inadimplentes = resp.json()
    alvo = next(i for i in inadimplentes if i["id"] == fatura_atrasada.id)
    assert alvo["status"] == "ATRASADO"
    assert alvo["juros_multa"] > 0.0  # Multa de 2% + juros pro-rata calculados


def deve_registrar_despesas_e_calcular_fluxo_de_caixa(client, admin_token, ambiente_fase5):
    hoje = date.today()
    # 1. Registra despesa de materiais de arte
    client.post(
        "/api/v1/financial/expenses",
        json={
            "categoria": "Materiais Artísticos",
            "descricao": "Tintas a óleo e telas para atelier",
            "valor": 150.0,
            "data_competencia": str(hoje),
            "data_pagamento": str(hoje),
            "pago": True,
            "forma_pagamento": "PIX"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 2. Registra receita (fatura paga)
    fat = client.post(
        "/api/v1/financial/invoices",
        json={
            "matricula_id": ambiente_fase5["matricula"].id,
            "aluno_id": ambiente_fase5["aluno"].id,
            "descricao": "Mensalidade Fluxo de Caixa",
            "competencia": hoje.strftime("%Y-%m"),
            "valor_nominal": 250.0,
            "desconto_aplicado": 0.0,
            "data_vencimento": str(hoje)
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    inv_id = fat.json()["id"]
    client.post(
        f"/api/v1/financial/invoices/{inv_id}/pay",
        json={"valor_pago": 250.0, "forma_pagamento": "PIX"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 3. Consulta fluxo de caixa
    resp = client.get(
        f"/api/v1/financial/cash-flow?data_inicio={hoje}&data_fim={hoje}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entradas"] >= 250.0
    assert data["total_saidas"] >= 150.0
    assert data["saldo_operacional"] == round(data["total_entradas"] - data["total_saidas"], 2)


def deve_gerar_dre_operacional(client, admin_token, ambiente_fase5):
    hoje = date.today()
    resp = client.get(
        f"/api/v1/financial/dre?competencia_inicio={hoje}&competencia_fim={hoje}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    dre = resp.json()
    assert "receita_bruta" in dre
    assert "deducoes_descontos" in dre
    assert "receita_liquida" in dre
    assert "despesas_operacionais" in dre
    assert "resultado_liquido" in dre
    assert dre["resultado_liquido"] == round(dre["receita_liquida"] - dre["despesas_operacionais"], 2)
