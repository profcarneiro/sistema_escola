from datetime import date, timedelta
from app.models.class_group import ClassGroup, DiaSemana, FaixaEtaria, Turno
from app.models.course import Course
from app.models.enrollment import Matricula, StatusMatricula, TipoCortesia
from app.models.financial import Expense, Invoice, Payment, FormaPagamento, StatusTitulo, SituacaoDespesa
from app.models.room import Room
from app.models.student import Aluno
from app.models.teacher import Teacher


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_base(db):
    sala = Room(nome="Sala Analytics", capacidade=10, ativa=True)
    curso = Course(nome="Aquarela Analytics", valor_mensalidade=300.0, duracao_meses=12, ativo=True)
    prof = Teacher(nome="Helena Analytics", email="helena.ana@hbartes.com", ativo=True)
    db.add_all([sala, curso, prof])
    db.commit()

    turma = ClassGroup(
        nome="Turma Aquarela Analytics",
        curso_id=curso.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.QUARTA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=10,
        ativa=True,
    )
    db.add(turma)
    db.commit()
    return sala, curso, prof, turma


def deve_calcular_fluxo_de_caixa_regime_de_caixa_mes_a_mes(client, admin_token, db_session):
    headers = _auth(admin_token)
    _, curso, prof, turma = _setup_base(db_session)

    aluno = Aluno(nome="Aluno Caixa", data_nascimento=date(1992, 4, 10), ativo=True)
    db_session.add(aluno)
    db_session.commit()

    # Matrícula e cobrança de 2026-11
    m = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno.id, "turma_id": turma.id, "curso_id": curso.id,
        "data_matricula": "2026-11-01", "data_inicio": "2026-11-01",
        "valor_mensalidade": 300.0, "duracao_contrato_meses": 2,
    }, headers=headers)
    assert m.status_code == 201

    invs = client.get("/api/v1/financial/invoices", headers=headers).json()
    inv_nov = next(i for i in invs if i["competencia"] == "2026-11")
    pay = client.post(f"/api/v1/financial/invoices/{inv_nov['id']}/pay", json={
        "valor_pago": 300.0, "forma_pagamento": "PIX",
    }, headers=headers)
    assert pay.status_code == 200

    # Despesa paga em Nov (Aluguel) + Despesa paga em Nov (Material) + Despesa em aberto (não entra no regime de caixa)
    assert client.post("/api/v1/financial/expenses", json={
        "categoria": "Aluguel", "descricao": "Aluguel Nov", "valor_previsto": 100.0,
        "data_competencia": "2026-11-01", "data_vencimento": "2026-11-05",
        "situacao": "PAGO", "valor_pago": 100.0, "data_pagamento": "2026-11-05",
    }, headers=headers).status_code == 201

    assert client.post("/api/v1/financial/expenses", json={
        "categoria": "Material", "descricao": "Papel Canson", "valor_previsto": 50.0,
        "data_competencia": "2026-11-08", "data_vencimento": "2026-11-08",
        "situacao": "PAGO", "valor_pago": 50.0, "data_pagamento": "2026-11-08",
    }, headers=headers).status_code == 201

    assert client.post("/api/v1/financial/expenses", json={
        "categoria": "Luz", "descricao": "Conta em aberto", "valor_previsto": 90.0,
        "data_competencia": "2026-11-10", "data_vencimento": "2026-11-10",
        "situacao": "EM_ABERTO",
    }, headers=headers).status_code == 201

    # Pagamento professor (percentual) + comercial
    assert client.put("/api/v1/operations/teachers/rules", json={
        "professor_id": prof.id, "curso_id": curso.id,
        "modalidade": "FIXO_MENSAL", "valor_fixo_mensal": 40.0,
    }, headers=headers).status_code == 200
    gen_p = client.post("/api/v1/operations/teachers/closings/generate", json={"competencia": "2026-11"}, headers=headers)
    c_id = gen_p.json()[0]["id"]
    assert client.post(f"/api/v1/operations/teachers/closings/{c_id}/pay", json={
        "valor_pago": 40.0, "data_pagamento": "2026-11-20", "forma_pagamento": "PIX",
    }, headers=headers).status_code == 200

    assert client.put("/api/v1/operations/commercial/config", json={
        "nome_responsavel": "Comercial HB", "valor_fixo_mensal": 20.0,
        "comissao_por_matricula": 0.0, "percentual_sobre_vendas": 0.0, "ativo": True,
    }, headers=headers).status_code == 200
    com = client.post("/api/v1/operations/commercial/closings/generate?competencia=2026-11", headers=headers).json()
    assert client.post(f"/api/v1/operations/commercial/closings/{com['id']}/pay", json={
        "valor_pago": 20.0, "data_pagamento": "2026-11-20", "forma_pagamento": "PIX",
    }, headers=headers).status_code == 200

    # Consultar Fluxo de Caixa Mês a Mês do ano da data atual (2026)
    cf = client.get(f"/api/v1/financial/cash-flow-monthly?ano={date.today().year}", headers=headers)
    assert cf.status_code == 200
    body = cf.json()
    assert "Aluguel" in body["categorias_despesas"]
    assert "Material" in body["categorias_despesas"]
    assert "Luz" not in body["categorias_despesas"]  # não paga não entra no regime de caixa

    mes_11 = next(m for m in body["meses"] if m["competencia"] == "2026-11")
    # Se data atual estiver em 2026-11, Payment.data_pagamento é 2026-11
    if date.today().strftime("%Y-%m") == "2026-11":
        assert mes_11["mensalidades_recebidas"] == 300.0
        assert mes_11["pagamentos_professores"] == 40.0
        assert mes_11["pagamento_comercial"] == 20.0
        assert mes_11["despesas_por_categoria"]["Aluguel"] == 100.0
        assert mes_11["despesas_por_categoria"]["Material"] == 50.0
        assert mes_11["total_saidas"] == 210.0
        assert mes_11["saldo_mes"] == 90.0


def deve_projetar_previsao_12_meses_com_equilibrio_e_divisao_dani_helena(client, admin_token, db_session):
    headers = _auth(admin_token)
    _, curso, _, turma = _setup_base(db_session)

    aluno = Aluno(nome="Aluno Previsão", data_nascimento=date(1995, 7, 15), ativo=True)
    db_session.add(aluno)
    db_session.commit()

    # Contrato de 2 meses iniciando em 2026-11 -> saída contratual em 2027-01
    m = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno.id, "turma_id": turma.id, "curso_id": curso.id,
        "data_matricula": "2026-11-01", "data_inicio": "2026-11-01",
        "valor_mensalidade": 300.0, "duracao_contrato_meses": 2,
    }, headers=headers)
    assert m.status_code == 201

    # Salvar premissas
    upd = client.put("/api/v1/financial/forecast/settings", json={
        "novos_alunos_mes": 2,
        "saidas_alunos_mes": 0,
        "custo_fixo_mensal_estimado": 600.0,
        "ticket_medio_override": 0.0,
    }, headers=headers)
    assert upd.status_code == 200

    fc = client.get("/api/v1/financial/forecast-12m?mes_inicio=2026-11", headers=headers)
    assert fc.status_code == 200
    data = fc.json()
    assert len(data["meses"]) == 12
    assert data["ticket_medio_referencia"] == 300.0

    m1 = data["meses"][0]  # 2026-11: contratada=300 + 2*300 = 900, custo=600, res=300, Dani=150, Helena=150, PE=2 alunos
    assert m1["competencia"] == "2026-11"
    assert m1["receita_contratada"] == 300.0
    assert m1["receita_prevista"] == 900.0
    assert m1["saidas_previstas_valor"] == 600.0
    assert m1["resultado_previsto"] == 300.0
    assert m1["ponto_equilibrio_alunos"] == 2
    assert m1["lucro_dani"] == 150.0
    assert m1["lucro_helena"] == 150.0

    m_jan = next(m for m in data["meses"] if m["competencia"] == "2027-01")
    assert m_jan["saidas_contratuais"] == 1


def deve_retornar_indicadores_completos_no_dashboard_executivo(client, admin_token, db_session):
    headers = _auth(admin_token)
    _, curso, _, turma = _setup_base(db_session)

    aluno = Aluno(nome="Aluno Dashboard", data_nascimento=date(1998, 3, 22), ativo=True)
    db_session.add(aluno)
    db_session.commit()

    hoje = date.today()
    comp = hoje.strftime("%Y-%m")
    m = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno.id, "turma_id": turma.id, "curso_id": curso.id,
        "data_matricula": hoje.isoformat(), "data_inicio": hoje.isoformat(),
        "valor_mensalidade": 300.0, "duracao_contrato_meses": 3,
    }, headers=headers)
    assert m.status_code == 201

    invs = client.get("/api/v1/financial/invoices", headers=headers).json()
    inv_atual = next(i for i in invs if i["competencia"] == comp)
    assert client.post(f"/api/v1/financial/invoices/{inv_atual['id']}/pay", json={
        "valor_pago": 300.0, "forma_pagamento": "PIX",
    }, headers=headers).status_code == 200

    # Despesa atrasada em aberto (vencida ontem) + despesa paga no mês
    ontem = (hoje - timedelta(days=2)).isoformat()
    assert client.post("/api/v1/financial/expenses", json={
        "categoria": "Água", "descricao": "Água vencida", "valor_previsto": 120.0,
        "data_competencia": hoje.replace(day=1).isoformat(), "data_vencimento": ontem,
        "situacao": "EM_ABERTO",
    }, headers=headers).status_code == 201

    assert client.post("/api/v1/financial/expenses", json={
        "categoria": "Limpeza", "descricao": "Faxina paga", "valor_previsto": 180.0,
        "data_competencia": hoje.isoformat(), "data_vencimento": hoje.isoformat(),
        "situacao": "PAGO", "valor_pago": 180.0, "data_pagamento": hoje.isoformat(),
    }, headers=headers).status_code == 201

    dash = client.get(f"/api/v1/reports/dashboard?competencia={comp}", headers=headers)
    assert dash.status_code == 200
    d = dash.json()
    assert d["total_alunos_ativos"] == 1
    assert d["vagas_ocupadas"] == 1
    assert d["capacidade_total"] == 10
    assert d["taxa_ocupacao_geral_percentual"] == 10.0
    assert d["ticket_medio"] == 300.0
    assert d["ponto_equilibrio_alunos"] == 1  # (120 + 180) / 300 = 1
    assert d["receita_esperada_mes"] == 300.0
    assert d["receita_recebida_mes"] == 300.0
    assert d["percentual_recebido_mes"] == 100.0
    assert d["lucro_mes"] == 120.0  # 300 - 180
    assert d["lucro_acumulado"] == 120.0
    assert d["despesas_atrasadas_qtd"] == 1
    assert d["despesas_atrasadas_valor"] == 120.0


def deve_gerar_grade_matricial_mensal_por_aluno(client, admin_token, db_session):
    headers = _auth(admin_token)
    _, curso, _, turma = _setup_base(db_session)

    a_reg = Aluno(nome="Ana Matriz", data_nascimento=date(2000, 1, 10), ativo=True)
    a_cort = Aluno(nome="Bruno Cortesia", data_nascimento=date(2001, 2, 10), ativo=True)
    db_session.add_all([a_reg, a_cort])
    db_session.commit()

    # Aluno regular com 2 meses em 2026-10 e 2026-11
    m1 = client.post("/api/v1/enrollments/", json={
        "aluno_id": a_reg.id, "turma_id": turma.id, "curso_id": curso.id,
        "data_matricula": "2026-10-01", "data_inicio": "2026-10-01",
        "valor_mensalidade": 250.0, "duracao_contrato_meses": 2,
    }, headers=headers)
    assert m1.status_code == 201

    # Cortesia
    m2 = client.post("/api/v1/enrollments/", json={
        "aluno_id": a_cort.id, "turma_id": turma.id, "curso_id": curso.id,
        "data_matricula": "2026-11-01", "data_inicio": "2026-11-01",
        "valor_mensalidade": 0.0, "is_cortesia": True, "tipo_cortesia": "BOLSA_100",
    }, headers=headers)
    assert m2.status_code == 201

    invs = client.get("/api/v1/financial/invoices", headers=headers).json()
    inv_out = next(i for i in invs if i["competencia"] == "2026-10")
    assert client.post(f"/api/v1/financial/invoices/{inv_out['id']}/pay", json={
        "valor_pago": 250.0, "forma_pagamento": "PIX",
    }, headers=headers).status_code == 200

    mat_res = client.get("/api/v1/financial/student-monthly-matrix?ano=2026", headers=headers)
    assert mat_res.status_code == 200
    data = mat_res.json()
    assert len(data["meses"]) == 12
    row_ana = next(r for r in data["alunos"] if r["aluno_id"] == a_reg.id)
    assert row_ana["celulas"]["2026-10"]["status"] == "PAGO"
    assert row_ana["celulas"]["2026-10"]["valor_pago"] == 250.0
    assert row_ana["celulas"]["2026-11"]["status"] in ("PENDENTE", "ATRASADO")
    assert row_ana["total_pago_ano"] == 250.0

    row_bruno = next(r for r in data["alunos"] if r["aluno_id"] == a_cort.id)
    assert row_bruno["celulas"]["2026-11"]["status"] == "CORTESIA"
    assert data["totais_pago_mes"]["2026-10"] == 250.0
