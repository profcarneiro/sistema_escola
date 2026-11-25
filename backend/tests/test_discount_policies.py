from datetime import date
import pytest

from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.student import Aluno
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno
from app.models.financial import Invoice


@pytest.fixture
def ambiente_politicas(db_session):
    sala = Room(nome="Sala Políticas", capacidade=12, ativa=True)
    curso1 = Course(nome="Ilustração de Moda", valor_mensalidade=280.0, duracao_meses=7, ativo=True)
    curso2 = Course(nome="Pintura em Tela", valor_mensalidade=300.0, duracao_meses=12, ativo=True)
    prof = Teacher(nome="Prof Políticas", email="prof.pol@hbartes.com", ativo=True)
    db_session.add_all([sala, curso1, curso2, prof])
    db_session.commit()

    turma = ClassGroup(
        nome="Turma Mista Políticas",
        curso_id=curso1.id,
        sala_id=sala.id,
        professor_id=prof.id,
        faixa_etaria=FaixaEtaria.ADULTO.value,
        dia_semana=DiaSemana.TERCA.value,
        turno=Turno.TARDE.value,
        horario_inicio="14:00",
        horario_fim="16:00",
        capacidade_maxima=12,
        ativa=True,
    )
    turma.cursos = [curso1, curso2]
    db_session.add(turma)
    db_session.commit()

    alunos = []
    for i in range(6):
        a = Aluno(nome=f"Aluno Política {i+1}", data_nascimento=date(1998, 5, 10), ativo=True)
        db_session.add(a)
        alunos.append(a)
    db_session.commit()

    return {
        "sala": sala,
        "curso_moda": curso1,
        "curso_pintura": curso2,
        "turma": turma,
        "alunos": alunos,
    }


def deve_configurar_planos_teto_e_regras_por_curso_sem_retroagir(client, admin_token, ambiente_politicas, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    pol = client.get("/api/v1/discount-policies/", headers=headers).json()
    planos = pol["planos"]
    a_vista = next(p for p in planos if p["codigo"] == "A_VISTA")
    irmao = next(p for p in planos if p["codigo"] == "IRMAO")
    indicacao = next(p for p in planos if p["codigo"] == "INDICACAO")

    # Configura teto máximo de 18%
    upd_teto = client.put("/api/v1/discount-policies/settings", json={"teto_maximo_desconto_percentual": 18.0}, headers=headers)
    assert upd_teto.status_code == 200
    assert upd_teto.json()["teto_maximo_desconto_percentual"] == 18.0

    # Soma À vista (10%) + Irmão (10%) + Indicação (5%) = 25%, limitado ao teto 18%
    sim = client.post(
        "/api/v1/discount-policies/simulate",
        json={
            "curso_id": ambiente_politicas["curso_pintura"].id,
            "valor_mensalidade": 300.0,
            "duracao_contrato_meses": 10,
            "condicao_pagamento": "A_VISTA",
            "plano_id": a_vista["id"],
            "descontos_ids": [irmao["id"], indicacao["id"]],
            "desconto_valor_fixo": 0.0,
        },
        headers=headers,
    ).json()
    assert sim["percentual_soma_sem_teto"] == 25.0
    assert sim["percentual_aplicado"] == 18.0
    assert sim["valor_total_bruto"] == 3000.0
    assert sim["valor_total_liquido"] == 2460.0

    # Regra por curso: Pintura em Tela SEM desconto à vista (0%)
    regra = client.put(
        "/api/v1/discount-policies/course-rules",
        json={
            "curso_id": ambiente_politicas["curso_pintura"].id,
            "plano_id": a_vista["id"],
            "permitido": False,
        },
        headers=headers,
    )
    assert regra.status_code == 200

    # Cria matrícula em Moda usando À vista (10%) antes de alterar o plano
    mat_antes = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][0].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_moda"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 280.0,
            "duracao_contrato_meses": 7,
            "condicao_pagamento": "A_VISTA",
            "plano_id": a_vista["id"],
        },
        headers=headers,
    )
    assert mat_antes.status_code == 201
    assert mat_antes.json()["desconto_percentual"] == 10.0

    # Altera À vista para 15%: NÃO pode retroagir na matrícula já criada
    upd_plan = client.put(
        f"/api/v1/discount-policies/plans/{a_vista['id']}",
        json={"percentual_desconto": 15.0},
        headers=headers,
    )
    assert upd_plan.status_code == 200

    mat_recheck = client.get(f"/api/v1/enrollments/{mat_antes.json()['id']}", headers=headers).json()
    assert mat_recheck["desconto_percentual"] == 10.0

    # Nova matrícula em Pintura em Tela com À vista deve respeitar bloqueio do curso (0%)
    mat_pintura = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][1].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_pintura"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 300.0,
            "duracao_contrato_meses": 5,
            "condicao_pagamento": "A_VISTA",
            "plano_id": a_vista["id"],
        },
        headers=headers,
    )
    assert mat_pintura.status_code == 201
    assert mat_pintura.json()["desconto_percentual"] == 0.0


def deve_gerar_faturas_para_a_vista_parcelado_mensal_e_cortesia(client, admin_token, ambiente_politicas, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    pol = client.get("/api/v1/discount-policies/", headers=headers).json()
    a_vista = next(p for p in pol["planos"] if p["codigo"] == "A_VISTA")

    # 1. Parcelado em 3x para contrato de 7 meses (7 x 280 = 1960)
    mat_parc = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][0].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_moda"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 280.0,
            "duracao_contrato_meses": 7,
            "condicao_pagamento": "PARCELADO",
            "quantidade_parcelas": 3,
        },
        headers=headers,
    )
    assert mat_parc.status_code == 201
    m_parc = mat_parc.json()
    assert m_parc["duracao_contrato_meses"] == 7
    assert m_parc["valor_total_contrato"] == 1960.0
    assert m_parc["total_parcelas_geradas"] == 3

    invs_parc = db_session.query(Invoice).filter(Invoice.matricula_id == m_parc["id"]).order_by(Invoice.id).all()
    assert len(invs_parc) == 3
    assert "Parcela 2/3 - Ilustração de Moda (parcelado)" in invs_parc[1].descricao
    assert round(sum(i.valor_final for i in invs_parc), 2) == 1960.0

    # 2. À vista com desconto (10%) -> 1 cobrança com descrição À vista
    mat_av = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][1].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_pintura"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 300.0,
            "duracao_contrato_meses": 4,
            "condicao_pagamento": "A_VISTA",
            "plano_id": a_vista["id"],
        },
        headers=headers,
    )
    assert mat_av.status_code == 201
    m_av = mat_av.json()
    assert m_av["total_parcelas_geradas"] == 1
    inv_av = db_session.query(Invoice).filter(Invoice.matricula_id == m_av["id"]).first()
    assert "À vista - Pintura em Tela (desconto 10%)" == inv_av.descricao
    assert inv_av.valor_nominal == 1200.0
    assert inv_av.desconto_aplicado == 120.0
    assert inv_av.valor_final == 1080.0

    # 3. Cortesia sem cobrança (BOLSA_100) + Desconto em R$ + Edição manual auditada + Data de saída
    mat_cort = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][2].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_moda"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "data_saida": "2026-12-20",
            "valor_mensalidade": 280.0,
            "duracao_contrato_meses": 6,
            "condicao_pagamento": "MENSAL",
            "is_cortesia": True,
            "tipo_cortesia": "BOLSA_100",
        },
        headers=headers,
    )
    assert mat_cort.status_code == 201
    assert mat_cort.json()["is_cortesia"] is True
    assert mat_cort.json()["tipo_cortesia"] == "BOLSA_100"
    assert mat_cort.json()["data_saida"] == "2026-12-20"
    assert mat_cort.json()["total_parcelas_geradas"] == 0

    # 4. Edição manual de desconto + R$ fixo + Relatório de descontos
    mat_manual = client.post(
        "/api/v1/enrollments/",
        json={
            "aluno_id": ambiente_politicas["alunos"][3].id,
            "turma_id": ambiente_politicas["turma"].id,
            "curso_id": ambiente_politicas["curso_moda"].id,
            "data_matricula": "2026-11-01",
            "data_inicio": "2026-11-05",
            "valor_mensalidade": 280.0,
            "duracao_contrato_meses": 2,
            "condicao_pagamento": "MENSAL",
            "plano_id": a_vista["id"],
            "desconto_percentual": 20.0,
            "desconto_valor_fixo": 40.0,
            "desconto_editado_manualmente": True,
            "desconto_motivo_alteracao": "Acordo diretoria",
        },
        headers=headers,
    )
    assert mat_manual.status_code == 201
    m_man = mat_manual.json()
    assert m_man["desconto_editado_manualmente"] is True
    assert m_man["desconto_alterado_por_nome"] == "Helena Barufaldi (Direção)"
    assert m_man["desconto_motivo_alteracao"] == "Acordo diretoria"

    rep = client.get("/api/v1/financial/discounts-report", headers=headers)
    assert rep.status_code == 200
    rep_data = rep.json()
    assert rep_data["total_descontos_concedidos"] > 0
    assert len(rep_data["por_tipo"]) >= 1
    assert len(rep_data["por_mes"]) >= 1
    assert any(a["matricula_id"] == m_man["id"] and a["motivo"] == "Acordo diretoria" for a in rep_data["alteracoes_manuais"])
