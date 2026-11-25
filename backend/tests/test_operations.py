from datetime import date, timedelta
from app.models.attendance import ClassMakeUp, Lesson, Attendance, StatusPresenca, StatusReposicao
from app.models.class_group import ClassGroup, DiaSemana, FaixaEtaria, Turno
from app.models.course import Course
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import FormaPagamento, Invoice, StatusTitulo
from app.models.room import Room
from app.models.student import Aluno
from app.models.teacher import Teacher


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_school(db):
    sala = Room(nome="Sala Teste Ops", capacidade=12, ativa=True)
    c_desenho = Course(nome="Desenho Artístico", valor_mensalidade=280.0, duracao_meses=12, ativo=True)
    c_aquarela = Course(nome="Pintura em Aquarela", valor_mensalidade=320.0, duracao_meses=6, ativo=True)
    p_ana = Teacher(nome="Ana Júlia", email="ana.ops@hbartes.com", ativo=True)
    p_helena = Teacher(nome="Helena", email="helena.ops@hbartes.com", ativo=True)
    db.add_all([sala, c_desenho, c_aquarela, p_ana, p_helena])
    db.commit()
    return sala, c_desenho, c_aquarela, p_ana, p_helena


def deve_gerenciar_despesas_recorrentes_parceladas_csv_e_dre(client, admin_token, db_session):
    headers = _auth(admin_token)
    sala, c_desenho, _, _, _ = _setup_school(db_session)

    # Centros de custo devem conter Gerais + Cursos
    ccs_res = client.get("/api/v1/financial/cost-centers", headers=headers)
    assert ccs_res.status_code == 200
    ccs = ccs_res.json()
    nomes_cc = {c["nome"] for c in ccs}
    assert {"Estrutura", "Administrativo", "Marketing e captação", "Ateliê - Parceria", "Sem centro (classificar)", "Desenho Artístico"}.issubset(nomes_cc)
    cc_estrutura = next(c for c in ccs if c["codigo"] == "ESTRUTURA")

    # 1) Despesa recorrente (Aluguel 3 meses)
    rec_res = client.post(
        "/api/v1/financial/expenses",
        json={
            "categoria": "Aluguel",
            "descricao": "Aluguel Ateliê",
            "valor_previsto": 2000.0,
            "data_competencia": "2026-11-01",
            "data_vencimento": "2026-11-05",
            "situacao": "PAGO",
            "valor_pago": 2000.0,
            "data_pagamento": "2026-11-05",
            "forma_pagamento": "TRANSFERENCIA",
            "centro_custo_id": cc_estrutura["id"],
            "recorrente": True,
            "recorrencia_meses": 3,
        },
        headers=headers,
    )
    assert rec_res.status_code == 201
    assert rec_res.json()["parcelas_criadas"] == 3
    assert rec_res.json()["situacao"] == "PAGO"

    # 2) Despesa parcelada (Material em 2x de R$ 300)
    parc_res = client.post(
        "/api/v1/financial/expenses",
        json={
            "categoria": "Material",
            "descricao": "Compra de Cavaletes",
            "valor_previsto": 300.0,
            "data_competencia": "2026-11-10",
            "data_vencimento": "2026-11-15",
            "situacao": "EM_ABERTO",
            "total_parcelas": 2,
        },
        headers=headers,
    )
    assert parc_res.status_code == 201
    assert parc_res.json()["parcelas_criadas"] == 2
    parc_id = parc_res.json()["id"]

    # Filtrar novembro/2026 (1 aluguel de 2000 + 1 parcela de 150)
    list_res = client.get("/api/v1/financial/expenses?ano=2026&mes=11", headers=headers)
    assert list_res.status_code == 200
    nov_items = list_res.json()
    assert len(nov_items) == 2

    # Editar/dar baixa na parcela 1/2
    upd = client.put(
        f"/api/v1/financial/expenses/{parc_id}",
        json={"situacao": "PAGO", "valor_pago": 145.0, "data_pagamento": "2026-11-15", "observacoes": "Desconto à vista"},
        headers=headers,
    )
    assert upd.status_code == 200
    assert upd.json()["pago"] is True
    assert upd.json()["valor"] == 145.0

    # DRE de nov/2026 deve refletir Despesas Op. = 2000 + 145 = 2145
    dre_res = client.get("/api/v1/financial/dre?competencia_inicio=2026-11-01&competencia_fim=2026-11-30", headers=headers)
    assert dre_res.status_code == 200
    assert dre_res.json()["despesas_operacionais"] == 2145.0

    # Exportar CSV
    csv_res = client.get("/api/v1/financial/expenses/export-csv?ano=2026&mes=11", headers=headers)
    assert csv_res.status_code == 200
    assert "Aluguel Ateliê" in csv_res.text

    # Excluir parcela
    del_res = client.delete(f"/api/v1/financial/expenses/{parc_id}", headers=headers)
    assert del_res.status_code == 200


def deve_calcular_fechamento_professores_e_bloquear_chamada_apos_fechamento(client, admin_token, professor_token, db_session):
    headers_admin = _auth(admin_token)
    headers_prof = _auth(professor_token)
    sala, c_desenho, c_aquarela, p_ana, p_helena = _setup_school(db_session)

    # Turmas e alunos
    t_desenho = ClassGroup(
        nome="Desenho Terça 14:30",
        curso_id=c_desenho.id,
        sala_id=sala.id,
        professor_id=p_ana.id,
        faixa_etaria=FaixaEtaria.INFANTIL.value,
        dia_semana=DiaSemana.TERCA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:30",
        horario_fim="16:00",
        capacidade_maxima=12,
        ativa=True,
    )
    t_aquarela = ClassGroup(
        nome="Aquarela Quarta 14:00",
        curso_id=c_aquarela.id,
        sala_id=sala.id,
        professor_id=p_helena.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.QUARTA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=12,
        ativa=True,
    )
    aluno_reg = Aluno(nome="Lucas Regular", data_nascimento=date(2014, 5, 10), ativo=True)
    aluno_exp = Aluno(nome="Mariana Experimental", data_nascimento=date(2015, 3, 20), ativo=True)
    aluno_just = Aluno(nome="Pedro Justificado", data_nascimento=date(2013, 1, 12), ativo=True)
    aluno_aqua = Aluno(nome="Beatriz Aquarela", data_nascimento=date(1990, 6, 1), ativo=True)
    db_session.add_all([t_desenho, t_aquarela, aluno_reg, aluno_exp, aluno_just, aluno_aqua])
    db_session.commit()

    # Configurar regras: Ana Júlia R$ 15/presença em Desenho; Helena 30% parcelado em Aquarela
    r1 = client.put("/api/v1/operations/teachers/rules", json={
        "professor_id": p_ana.id, "curso_id": c_desenho.id, "modalidade": "POR_PRESENCA",
        "valor_por_presenca": 15.0, "pagar_experimental": False, "pagar_cortesia": False,
    }, headers=headers_admin)
    assert r1.status_code == 200
    r2 = client.put("/api/v1/operations/teachers/rules", json={
        "professor_id": p_helena.id, "curso_id": c_aquarela.id, "modalidade": "PERCENTUAL",
        "percentual_curso": 30.0, "pagamento_percentual_modo": "PARCELADO_MENSAL",
    }, headers=headers_admin)
    assert r2.status_code == 200

    # Matrículas via API para gerar faturas com centro de custo
    m_reg = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno_reg.id, "turma_id": t_desenho.id, "curso_id": c_desenho.id,
        "data_matricula": "2026-11-01", "data_inicio": "2026-11-01", "valor_mensalidade": 280.0, "duracao_contrato_meses": 2,
    }, headers=headers_admin)
    assert m_reg.status_code == 201
    m_reg_id = m_reg.json()["id"]

    m_exp = Matricula(
        aluno_id=aluno_exp.id, turma_id=t_desenho.id, curso_id=c_desenho.id,
        status=StatusMatricula.EXPERIMENTAL.value, data_matricula=date(2026, 11, 1), data_inicio=date(2026, 11, 1),
        valor_mensalidade=0.0, aula_experimental=True, numero_contrato="EXP-OPS-1",
    )
    m_just = Matricula(
        aluno_id=aluno_just.id, turma_id=t_desenho.id, curso_id=c_desenho.id,
        status=StatusMatricula.ATIVA.value, data_matricula=date(2026, 11, 1), data_inicio=date(2026, 11, 1),
        valor_mensalidade=280.0, numero_contrato="REG-OPS-2",
    )
    db_session.add_all([m_exp, m_just])
    db_session.commit()

    # Matrícula em Aquarela (R$ 300/mês) -> comissão Helena = 30% = R$ 90
    m_aqua = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno_aqua.id, "turma_id": t_aquarela.id, "curso_id": c_aquarela.id,
        "data_matricula": "2026-11-01", "data_inicio": "2026-11-01", "valor_mensalidade": 300.0, "duracao_contrato_meses": 2,
    }, headers=headers_admin)
    assert m_aqua.status_code == 201

    # Aula 1 válida (Ana Júlia): 1 regular PRESENTE (+15) + 1 experimental PRESENTE (0) + 1 JUSTIFICADA (0) + 1 reposição (+15)
    l1 = client.post("/api/v1/attendance/lessons", json={
        "turma_id": t_desenho.id, "professor_id": p_ana.id,
        "data_aula": "2026-11-03", "tema_aula": "Sombreamento",
    }, headers=headers_admin)
    assert l1.status_code == 201
    l1_id = l1.json()["id"]

    att1 = client.post(f"/api/v1/attendance/lessons/{l1_id}/batch", json={
        "frequencias": [
            {"aluno_id": aluno_reg.id, "matricula_id": m_reg_id, "status": "PRESENTE"},
            {"aluno_id": aluno_exp.id, "matricula_id": m_exp.id, "status": "PRESENTE"},
            {"aluno_id": aluno_just.id, "matricula_id": m_just.id, "status": "JUSTIFICADA", "motivo_justificativa": "Atestado"},
            {"aluno_id": aluno_aqua.id, "matricula_id": m_aqua.json()["id"], "status": "PRESENTE", "eh_reposicao": True},
        ]
    }, headers=headers_admin)
    assert att1.status_code == 201

    # Aula 2 cancelada pelo professor (sem pagamento mesmo com chamada)
    l2 = client.post("/api/v1/attendance/lessons", json={
        "turma_id": t_desenho.id, "professor_id": p_ana.id,
        "data_aula": "2026-11-10", "tema_aula": "Cancelada", "cancelada_professor": True,
    }, headers=headers_admin)
    assert l2.status_code == 201

    # Gerar fechamento 2026-11
    gen = client.post("/api/v1/operations/teachers/closings/generate", json={"competencia": "2026-11"}, headers=headers_admin)
    assert gen.status_code == 200
    closings = {c["professor_id"]: c for c in gen.json()}

    c_ana = closings[p_ana.id]
    assert c_ana["total_aulas_dadas"] == 1  # aula cancelada não conta
    assert c_ana["total_presencas"] == 2  # regular + reposição
    assert c_ana["valor_por_presenca_total"] == 30.0
    assert c_ana["valor_total"] == 30.0

    c_helena = closings[p_helena.id]
    assert c_helena["valor_percentual_total"] == 90.0  # 30% de 300

    # Pagar e conciliar com extrato
    pay = client.post(f"/api/v1/operations/teachers/closings/{c_ana['id']}/pay", json={
        "valor_pago": 30.0, "data_pagamento": "2026-11-30", "forma_pagamento": "PIX",
        "conciliado_extrato": True, "referencia_extrato": "EXTRATO-PIX-123",
    }, headers=headers_admin)
    assert pay.status_code == 200
    assert pay.json()["status"] == "PAGO"
    assert pay.json()["conciliado_extrato"] is True

    # Professor NÃO consegue alterar chamada após fechamento/pagamento (409)
    blocked = client.post(f"/api/v1/attendance/lessons/{l1_id}/batch", json={
        "frequencias": [{"aluno_id": aluno_just.id, "matricula_id": m_just.id, "status": "PRESENTE"}]
    }, headers=headers_prof)
    assert blocked.status_code == 409

    # Direção consegue alterar informando motivo_alteracao e registra no log
    override = client.post(f"/api/v1/attendance/lessons/{l1_id}/batch", json={
        "frequencias": [{"aluno_id": aluno_just.id, "matricula_id": m_just.id, "status": "FALTA"}],
        "motivo_alteracao": "Correção solicitada pela secretaria",
    }, headers=headers_admin)
    assert override.status_code == 201
    logs = client.get("/api/v1/operations/teachers/change-logs?competencia=2026-11", headers=headers_admin)
    assert logs.status_code == 200
    assert any(lg["motivo"] == "Correção solicitada pela secretaria" for lg in logs.json())

    # Relatório por centro de custo deve vincular receitas e custos de professores aos cursos
    cc_rep = client.get("/api/v1/financial/cost-centers/report?ano=2026&mes=11", headers=headers_admin)
    assert cc_rep.status_code == 200
    centros_map = {c["nome"]: c for c in cc_rep.json()["centros"]}
    assert centros_map["Desenho Artístico"]["receita_prevista_total"] == 280.0
    assert centros_map["Desenho Artístico"]["custo_realizado_total"] == 30.0
    assert centros_map["Pintura em Aquarela"]["receita_prevista_total"] == 300.0
    assert centros_map["Pintura em Aquarela"]["custo_previsto_total"] == 90.0

    # Relatório mensal por aluno
    m_rep = client.get("/api/v1/attendance/reports/monthly-students?competencia=2026-11", headers=headers_admin)
    assert m_rep.status_code == 200
    assert len(m_rep.json()) >= 3

    # Alerta de aula sem chamada
    l_sem_chamada = client.post("/api/v1/attendance/lessons", json={
        "turma_id": t_aquarela.id, "professor_id": p_helena.id,
        "data_aula": date.today().isoformat(), "tema_aula": "Aula sem chamada",
    }, headers=headers_admin)
    assert l_sem_chamada.status_code == 201
    al_res = client.get("/api/v1/attendance/alerts/missing-calls", headers=headers_admin)
    assert al_res.status_code == 200
    assert any(a["lesson_id"] == l_sem_chamada.json()["id"] for a in al_res.json())


def deve_calcular_comercial_e_atelie_parceria_50_50(client, admin_token, db_session):
    headers = _auth(admin_token)
    sala, c_desenho, _, p_ana, _ = _setup_school(db_session)

    turma = ClassGroup(
        nome="Turma Venda Comercial", curso_id=c_desenho.id, sala_id=sala.id, professor_id=p_ana.id,
        faixa_etaria=FaixaEtaria.ADULTO.value, dia_semana=DiaSemana.SEGUNDA.value,
        turno=Turno.NOITE.value, horario_inicio="19:00", horario_fim="21:00", capacidade_maxima=12, ativa=True,
    )
    aluno = Aluno(nome="Aluno Novo Comercial", data_nascimento=date(1995, 2, 2), ativo=True)
    db_session.add_all([turma, aluno])
    db_session.commit()

    # Nova matrícula em 2026-11 (2 meses * 280 = R$ 560 líquido)
    m_res = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno.id, "turma_id": turma.id, "curso_id": c_desenho.id,
        "data_matricula": "2026-11-05", "data_inicio": "2026-11-05", "valor_mensalidade": 280.0, "duracao_contrato_meses": 2,
    }, headers=headers)
    assert m_res.status_code == 201

    # Comercial: fixo 1000 + 50 por matrícula + 10% sobre vendas (1000 + 50 + 56 = 1106)
    cfg = client.put("/api/v1/operations/commercial/config", json={
        "nome_responsavel": "Comercial HB", "valor_fixo_mensal": 1000.0,
        "comissao_por_matricula": 50.0, "percentual_sobre_vendas": 10.0, "ativo": True,
    }, headers=headers)
    assert cfg.status_code == 200

    com_gen = client.post("/api/v1/operations/commercial/closings/generate?competencia=2026-11", headers=headers)
    assert com_gen.status_code == 200
    payout = com_gen.json()
    assert payout["qtd_matriculas_novas"] == 1
    assert payout["total_vendas_mes"] == 560.0
    assert payout["total_devido"] == 1106.0

    com_pay = client.post(f"/api/v1/operations/commercial/closings/{payout['id']}/pay", json={
        "valor_pago": 500.0, "data_pagamento": "2026-11-30", "forma_pagamento": "PIX",
    }, headers=headers)
    assert com_pay.status_code == 200
    assert com_pay.json()["saldo"] == 606.0

    # Ateliê - Parceria 50/50
    ws = client.post("/api/v1/operations/workshops", json={
        "titulo": "Oficina Esmaltação", "modalidade": "Esmaltação em Cerâmica",
        "professora_parceira": "Parceira Cerâmica", "data_realizacao": "2026-11-21",
        "percentual_escola": 50.0, "percentual_professora": 50.0, "despesas_materiais": 40.0,
        "participantes": [
            {"aluno_nome": "Avulso 1", "valor_pago": 180.0, "forma_pagamento": "PIX"},
            {"aluno_nome": "Avulso 2", "valor_pago": 180.0, "forma_pagamento": "DINHEIRO"},
        ],
    }, headers=headers)
    assert ws.status_code == 201
    ws_data = ws.json()
    assert ws_data["receita_bruta"] == 360.0
    assert ws_data["parte_escola"] == 180.0
    assert ws_data["valor_repassar_professora"] == 180.0
    assert ws_data["resultado_escola"] == 140.0  # 180 - 40 materiais

    rep = client.post(f"/api/v1/operations/workshops/{ws_data['id']}/pay-transfer", json={
        "data_repasse": "2026-11-25", "forma_repasse": "TRANSFERENCIA",
    }, headers=headers)
    assert rep.status_code == 200
    assert rep.json()["repasse_pago"] is True

    sum_res = client.get("/api/v1/operations/workshops/summary?competencia=2026-11", headers=headers)
    assert sum_res.status_code == 200
    s = sum_res.json()
    assert s["receita_total"] == 360.0
    assert s["valor_ja_repassado"] == 180.0
    assert s["saldo_a_repassar"] == 0.0
    assert s["resultado_liquido_escola"] == 140.0
