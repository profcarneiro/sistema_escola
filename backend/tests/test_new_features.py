import pytest
from datetime import date
from app.models.user import UserRole
from app.models.enrollment import StatusMatricula
from app.models.financial import StatusTitulo


def test_atualizar_aluno_e_responsavel(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Cadastra aluno
    resp = client.post("/api/v1/students/", json={
        "nome": "Aluno Teste Atualizacao",
        "data_nascimento": "2000-01-15",
        "cpf": "12345678901",
        "email": "aluno.atualiza@teste.com",
        "telefone": "19999990001",
        "endereco": "Rua 1, Nova Odessa",
        "autorizacao_imagem": True
    }, headers=headers)
    assert resp.status_code == 201
    aluno_id = resp.json()["id"]

    # Atualiza dados do aluno
    update_resp = client.put(f"/api/v1/students/{aluno_id}", json={
        "nome": "Aluno Teste Nome Atualizado",
        "data_nascimento": "2000-02-20",
        "telefone": "19988880002"
    }, headers=headers)
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["nome"] == "Aluno Teste Nome Atualizado"
    assert data["data_nascimento"] == "2000-02-20"
    assert data["telefone"] == "19988880002"


def test_gerar_matricula_com_parcelas_e_dia_vencimento(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Cria aluno
    aluno_resp = client.post("/api/v1/students/", json={
        "nome": "Aluno Parcelas Teste",
        "data_nascimento": "1995-05-10",
        "cpf": "99988877766",
        "email": "aluno.parcelas@teste.com"
    }, headers=headers)
    aluno_id = aluno_resp.json()["id"]

    # Cria curso e sala
    curso_resp = client.post("/api/v1/courses/", json={
        "nome": "Curso Escultura Teste",
        "duracao_meses": 12,
        "valor_mensalidade": 300.0
    }, headers=headers)
    curso_id = curso_resp.json()["id"]

    sala_resp = client.post("/api/v1/rooms/", json={
        "nome": "Sala Escultura",
        "capacidade": 9
    }, headers=headers)
    sala_id = sala_resp.json()["id"]

    prof_resp = client.post("/api/v1/teachers/", json={
        "nome": "Professor Escultura",
        "email": "prof.escultura@teste.com"
    }, headers=headers)
    prof_id = prof_resp.json()["id"]

    turma_resp = client.post("/api/v1/classes/", json={
        "nome": "Turma Escultura Noturno",
        "curso_id": curso_id,
        "sala_id": sala_id,
        "professor_id": prof_id,
        "dia_semana": "TERCA",
        "turno": "NOITE",
        "horario_inicio": "19:00",
        "horario_fim": "21:00",
        "capacidade_maxima": 9,
        "faixa_etaria": "ADULTO"
    }, headers=headers)
    turma_id = turma_resp.json()["id"]

    # Matrícula com 6 parcelas e dia de vencimento 15
    mat_resp = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno_id,
        "turma_id": turma_id,
        "data_matricula": str(date.today()),
        "data_inicio": str(date.today()),
        "valor_mensalidade": 300.0,
        "desconto_percentual": 10.0,
        "tipo_desconto": "indicacao",
        "dia_vencimento": 15,
        "quantidade_parcelas": 6,
        "aula_experimental": False
    }, headers=headers)
    assert mat_resp.status_code == 201
    mat_data = mat_resp.json()
    assert mat_data["dia_vencimento"] == 15
    assert mat_data["quantidade_parcelas"] == 6

    # Verifica faturas geradas
    invoices_resp = client.get(f"/api/v1/financial/invoices?aluno_id={aluno_id}", headers=headers)
    assert invoices_resp.status_code == 200
    invoices = invoices_resp.json()
    assert len(invoices) == 6
    # Valor 300 com 10% desc = 270
    assert invoices[0]["valor_final"] == 270.0
    assert invoices[0]["desconto_aplicado"] == 30.0
    assert invoices[0]["status"] in ["PENDENTE", "ATRASADO"]

    # Realiza pagamento da primeira fatura
    fatura_id = invoices[0]["id"]
    pay_resp = client.post(f"/api/v1/financial/invoices/{fatura_id}/pay", json={
        "valor_pago": 270.0,
        "forma_pagamento": "PIX",
        "comprovante_transacao": "PIX-123456",
        "observacoes": "Pago no balcao"
    }, headers=headers)
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "PAGO"


def test_relatorio_frequencia_turmas_e_alunos(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Cria estrutura
    aluno_resp = client.post("/api/v1/students/", json={
        "nome": "Aluno Frequencia",
        "data_nascimento": "1998-03-20",
        "cpf": "11122233344",
        "email": "aluno.freq@teste.com"
    }, headers=headers)
    aluno_id = aluno_resp.json()["id"]

    curso_resp = client.post("/api/v1/courses/", json={
        "nome": "Curso Frequencia",
        "duracao_meses": 6,
        "valor_mensalidade": 200.0
    }, headers=headers)
    curso_id = curso_resp.json()["id"]

    sala_resp = client.post("/api/v1/rooms/", json={
        "nome": "Sala Freq",
        "capacidade": 9
    }, headers=headers)
    sala_id = sala_resp.json()["id"]

    prof_resp = client.post("/api/v1/teachers/", json={
        "nome": "Professor Freq",
        "email": "prof.freq@teste.com"
    }, headers=headers)
    prof_id = prof_resp.json()["id"]

    turma_resp = client.post("/api/v1/classes/", json={
        "nome": "Turma Freq",
        "curso_id": curso_id,
        "sala_id": sala_id,
        "professor_id": prof_id,
        "dia_semana": "QUARTA",
        "turno": "TARDE",
        "horario_inicio": "14:00",
        "horario_fim": "16:00",
        "capacidade_maxima": 9,
        "faixa_etaria": "ADULTO"
    }, headers=headers)
    turma_id = turma_resp.json()["id"]

    mat_resp = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno_id,
        "turma_id": turma_id,
        "data_matricula": str(date.today()),
        "data_inicio": str(date.today()),
        "valor_mensalidade": 200.0,
        "dia_vencimento": 10,
        "quantidade_parcelas": 1
    }, headers=headers)
    matricula_id = mat_resp.json()["id"]

    # Cria aula e presença
    lesson_resp = client.post("/api/v1/attendance/lessons", json={
        "turma_id": turma_id,
        "professor_id": prof_id,
        "data_aula": str(date.today()),
        "tema_aula": "Introducao a Tecnica",
        "conteudo_programatico": "Pintura base",
        "materiais_utilizados": "Tinta acrilica"
    }, headers=headers)
    assert lesson_resp.status_code == 201
    lesson_id = lesson_resp.json()["id"]

    att_resp = client.post(f"/api/v1/attendance/lessons/{lesson_id}/batch", json={
        "frequencias": [{
            "aluno_id": aluno_id,
            "matricula_id": matricula_id,
            "status": "PRESENTE"
        }]
    }, headers=headers)
    assert att_resp.status_code == 201

    # Relatório de turmas
    rep_classes = client.get("/api/v1/attendance/reports/classes-summary", headers=headers)
    assert rep_classes.status_code == 200
    classes_summary = rep_classes.json()
    assert any(c["turma_id"] == turma_id for c in classes_summary)
    turma_item = next(c for c in classes_summary if c["turma_id"] == turma_id)
    assert turma_item["total_matriculados"] == 1
    assert turma_item["capacidade_maxima"] == 9
    assert "QUARTA" in turma_item["dia_semana"]

    # Relatório do aluno
    rep_student = client.get(f"/api/v1/attendance/reports/student-history?aluno_id={aluno_id}", headers=headers)
    assert rep_student.status_code == 200
    student_summary = rep_student.json()
    assert student_summary["aluno_id"] == aluno_id
    assert student_summary["total_presencas"] == 1
    assert student_summary["taxa_presenca_percentual"] == 100.0
    # Verifica compatibilidade dos campos registros e historico
    assert "registros" in student_summary and len(student_summary["registros"]) == 1
    assert "historico" in student_summary and len(student_summary["historico"]) == 1
    assert student_summary["registros"][0]["status"] == "PRESENTE"


def test_gerenciamento_usuarios_e_escopo_professor(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Testa criação de usuário administrador usando formato DIRECAO
    admin_novo_resp = client.post("/api/v1/users/", json={
        "nome": "Novo Administrador Geral",
        "email": "novo.admin@teste.com",
        "senha": "adminSenhaSegura123",
        "role": "DIRECAO",
        "ativo": True
    }, headers=headers)
    assert admin_novo_resp.status_code == 201
    assert admin_novo_resp.json()["role"] == "Direção"

    # Cria professor
    prof_resp = client.post("/api/v1/teachers/", json={
        "nome": "Professor Escopo",
        "email": "prof.escopo@teste.com"
    }, headers=headers)
    prof_id = prof_resp.json()["id"]

    # Cria usuário com perfil Professor vinculado ao professor
    user_resp = client.post("/api/v1/users/", json={
        "nome": "Professor Escopo User",
        "email": "prof.escopo@teste.com",
        "senha": "senhaSegura123",
        "role": "Professor",
        "professor_id": prof_id,
        "ativo": True
    }, headers=headers)
    assert user_resp.status_code == 201
    user_data = user_resp.json()
    assert user_data["role"] == "Professor"
    assert user_data["professor_id"] == prof_id

    # Faz login como professor
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "prof.escopo@teste.com",
        "senha": "senhaSegura123"
    })
    assert login_resp.status_code == 200
    prof_token = login_resp.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    # Professor busca turmas - deve vir apenas as turmas vinculadas a ele (atualmente 0)
    turmas_resp = client.get("/api/v1/classes/", headers=prof_headers)
    assert turmas_resp.status_code == 200
    assert len(turmas_resp.json()) == 0


def test_converter_experimental_para_ativa_e_sincronizar_parcelas(client, admin_token, db_session):
    from app.models.financial import Invoice
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Cria aluno, curso, sala, professor e turma
    aluno_id = client.post("/api/v1/students/", json={
        "nome": "Aluno Experimental",
        "data_nascimento": "1999-04-12",
        "cpf": "55544433322"
    }, headers=headers).json()["id"]

    curso_id = client.post("/api/v1/courses/", json={
        "nome": "Curso Ceramica Sync",
        "duracao_meses": 12,
        "valor_mensalidade": 320.0
    }, headers=headers).json()["id"]

    sala_id = client.post("/api/v1/rooms/", json={"nome": "Sala Sync", "capacidade": 9}, headers=headers).json()["id"]
    prof_id = client.post("/api/v1/teachers/", json={"nome": "Prof Sync", "email": "prof.sync@teste.com"}, headers=headers).json()["id"]
    turma_id = client.post("/api/v1/classes/", json={
        "nome": "Turma Sync",
        "curso_id": curso_id,
        "sala_id": sala_id,
        "professor_id": prof_id,
        "dia_semana": "SEXTA",
        "turno": "MANHA",
        "horario_inicio": "09:00",
        "horario_fim": "11:00",
        "capacidade_maxima": 9,
        "faixa_etaria": "ADULTO"
    }, headers=headers).json()["id"]

    # 1. Cria matrícula experimental -> não deve gerar parcelas
    mat_exp = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno_id,
        "turma_id": turma_id,
        "data_matricula": str(date.today()),
        "data_inicio": str(date.today()),
        "valor_mensalidade": 320.0,
        "dia_vencimento": 10,
        "quantidade_parcelas": 4,
        "aula_experimental": True
    }, headers=headers)
    assert mat_exp.status_code == 201
    mat_id = mat_exp.json()["id"]
    assert mat_exp.json()["total_parcelas_geradas"] == 0

    invs = client.get(f"/api/v1/financial/invoices?aluno_id={aluno_id}", headers=headers).json()
    assert len(invs) == 0

    # 2. Atualiza para ATIVA -> deve gerar automaticamente as 4 parcelas
    upd = client.put(f"/api/v1/enrollments/{mat_id}", json={"status": "ATIVA"}, headers=headers)
    assert upd.status_code == 200
    assert upd.json()["total_parcelas_geradas"] == 4

    invs = client.get(f"/api/v1/financial/invoices?aluno_id={aluno_id}", headers=headers).json()
    assert len(invs) == 4

    # 3. Remove parcelas simulando matrícula legada sem parcelas e testa sync + endpoint por matrícula
    db_session.query(Invoice).filter(Invoice.matricula_id == mat_id).delete()
    db_session.commit()

    gen_resp = client.post(f"/api/v1/enrollments/{mat_id}/generate-invoices", headers=headers)
    assert gen_resp.status_code == 200
    assert gen_resp.json()["parcelas_geradas"] == 4

    # Sync em lote não deve duplicar parcelas já geradas
    sync_resp = client.post("/api/v1/financial/invoices/sync-enrollments", headers=headers)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["parcelas_geradas"] == 0

    # 4. Matrícula com valor 0 (bolsa 100%) não deve quebrar GET /financial/invoices
    aluno2_id = client.post("/api/v1/students/", json={
        "nome": "Aluno Bolsa Zero",
        "data_nascimento": "1998-01-10",
        "cpf": "77766655544"
    }, headers=headers).json()["id"]
    mat_zero = client.post("/api/v1/enrollments/", json={
        "aluno_id": aluno2_id,
        "turma_id": turma_id,
        "data_matricula": str(date.today()),
        "data_inicio": str(date.today()),
        "valor_mensalidade": 0.0,
        "dia_vencimento": 10,
        "quantidade_parcelas": 2,
        "aula_experimental": False
    }, headers=headers)
    assert mat_zero.status_code == 201
    all_invs = client.get("/api/v1/financial/invoices", headers=headers)
    assert all_invs.status_code == 200
    assert len(all_invs.json()) == 6
