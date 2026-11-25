import calendar
import csv
import io
import math
from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.student import Aluno
from app.models.room import Room
from app.models.class_group import ClassGroup
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Invoice, Payment, Expense, StatusTitulo
from app.models.operations import WorkshopSession
from app.models.user import User, UserRole
from app.routers.auth import get_current_active_user, require_roles
from app.routers.enrollments import contar_matriculas_ativas
from app.routers.financial import calcular_ticket_medio_escola

router = APIRouter(prefix="/reports", tags=["Relatórios e Dashboards"])


class DashboardSummary(BaseModel):
    competencia: str
    total_alunos_ativos: int
    total_alunos_inativos: int
    total_turmas_ativas: int
    vagas_ocupadas: int
    capacidade_total: int
    taxa_ocupacao_geral_percentual: float
    ticket_medio: float
    ponto_equilibrio_alunos: int
    ponto_equilibrio_valor: float
    receita_esperada_mes: float
    receita_recebida_mes: float
    percentual_recebido_mes: float
    despesas_previstas_mes: float
    despesas_pagas_mes: float
    lucro_mes: float
    lucro_acumulado: float
    despesas_atrasadas_qtd: int
    despesas_atrasadas_valor: float
    total_faturas_abertas: int
    total_inadimplentes: int
    valor_total_inadimplente: float


class RoomOccupancyReport(BaseModel):
    sala_nome: str
    capacidade_sala: int
    turmas: List[Dict[str, Any]]
    ocupacao_media_sala_percentual: float


@router.get("/dashboard", response_model=DashboardSummary, summary="Dashboard executivo gerencial")
def get_dashboard_summary(
    competencia: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM (padrão mês atual)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    hoje = date.today()
    if competencia:
        ano, mes = map(int, competencia.split("-"))
    else:
        ano, mes = hoje.year, hoje.month
    comp_str = f"{ano:04d}-{mes:02d}"
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])

    alunos_ativos = db.query(Aluno).filter(Aluno.ativo.is_(True)).count()
    alunos_inativos = db.query(Aluno).filter(Aluno.ativo.is_(False)).count()
    turmas_ativas = db.query(ClassGroup).filter(ClassGroup.ativa.is_(True)).all()

    capacidade_total = sum(t.capacidade_maxima for t in turmas_ativas) if turmas_ativas else 0
    vagas_ocupadas = sum(contar_matriculas_ativas(db, t.id) for t in turmas_ativas)
    taxa_ocupacao = round((vagas_ocupadas / capacidade_total) * 100, 2) if capacidade_total > 0 else 0.0

    # Ticket médio e ponto de equilíbrio
    ticket_medio = calcular_ticket_medio_escola(db)

    # Receita esperada vs recebida no mês
    faturas_mes = db.query(Invoice).filter(
        Invoice.competencia == comp_str,
        Invoice.status != StatusTitulo.CANCELADO.value,
    ).all()
    receita_esperada_mes = round(sum(float(i.valor_final or 0.0) for i in faturas_mes), 2)

    pagamentos_mes = db.query(Payment).filter(
        func.date(Payment.data_pagamento) >= inicio_mes,
        func.date(Payment.data_pagamento) <= fim_mes,
    ).all()
    workshops_mes = db.query(WorkshopSession).options(
        joinedload(WorkshopSession.participantes)
    ).filter(
        WorkshopSession.data_realizacao >= inicio_mes,
        WorkshopSession.data_realizacao <= fim_mes,
    ).all()
    receita_ws_mes = sum(sum(float(pt.valor_pago or 0.0) for pt in (w.participantes or [])) for w in workshops_mes)
    receita_recebida_mes = round(sum(float(p.valor_pago or 0.0) for p in pagamentos_mes) + receita_ws_mes, 2)
    percentual_recebido_mes = (
        round((receita_recebida_mes / receita_esperada_mes) * 100, 2)
        if receita_esperada_mes > 0
        else 0.0
    )

    # Despesas do mês (previstas e pagas)
    despesas_comp = db.query(Expense).filter(
        Expense.data_competencia >= inicio_mes,
        Expense.data_competencia <= fim_mes,
    ).all()
    despesas_previstas_mes = round(
        sum(float(d.valor_previsto if d.valor_previsto is not None else (d.valor or 0.0)) for d in despesas_comp),
        2,
    )

    despesas_pagas_mes_rows = db.query(Expense).filter(
        Expense.pago.is_(True),
        Expense.data_pagamento >= inicio_mes,
        Expense.data_pagamento <= fim_mes,
    ).all()
    despesas_pagas_mes = round(
        sum(float(d.valor_pago if (d.valor_pago and d.valor_pago > 0) else (d.valor or 0.0)) for d in despesas_pagas_mes_rows),
        2,
    )

    ponto_equilibrio_alunos = (
        math.ceil(despesas_previstas_mes / ticket_medio)
        if (despesas_previstas_mes > 0 and ticket_medio > 0)
        else 0
    )

    lucro_mes = round(receita_recebida_mes - despesas_pagas_mes, 2)

    # Lucro acumulado (regime de caixa histórico até fim do mês selecionado)
    pagamentos_acum = db.query(Payment).filter(func.date(Payment.data_pagamento) <= fim_mes).all()
    workshops_acum = db.query(WorkshopSession).options(
        joinedload(WorkshopSession.participantes)
    ).filter(WorkshopSession.data_realizacao <= fim_mes).all()
    total_rec_acum = sum(float(p.valor_pago or 0.0) for p in pagamentos_acum) + sum(
        sum(float(pt.valor_pago or 0.0) for pt in (w.participantes or [])) for w in workshops_acum
    )
    despesas_pagas_acum = db.query(Expense).filter(
        Expense.pago.is_(True),
        Expense.data_pagamento <= fim_mes,
    ).all()
    total_desp_acum = sum(
        float(d.valor_pago if (d.valor_pago and d.valor_pago > 0) else (d.valor or 0.0))
        for d in despesas_pagas_acum
    )
    lucro_acumulado = round(total_rec_acum - total_desp_acum, 2)

    # Despesas atrasadas
    despesas_em_aberto = db.query(Expense).filter(Expense.pago.is_(False)).all()
    despesas_atrasadas = [
        d for d in despesas_em_aberto
        if (d.data_vencimento or d.data_competencia) < hoje
    ]
    despesas_atrasadas_qtd = len(despesas_atrasadas)
    despesas_atrasadas_valor = round(
        sum(float(d.valor_previsto if d.valor_previsto is not None else (d.valor or 0.0)) for d in despesas_atrasadas),
        2,
    )

    # Inadimplência
    inadimplentes = db.query(Invoice).filter(
        Invoice.status.in_([StatusTitulo.PENDENTE.value, StatusTitulo.ATRASADO.value]),
        Invoice.data_vencimento < hoje
    ).all()

    total_inadimplentes = len(inadimplentes)
    valor_inadimplente = round(sum(i.valor_final for i in inadimplentes), 2)
    faturas_abertas = db.query(Invoice).filter(Invoice.status == StatusTitulo.PENDENTE.value).count()

    return DashboardSummary(
        competencia=comp_str,
        total_alunos_ativos=alunos_ativos,
        total_alunos_inativos=alunos_inativos,
        total_turmas_ativas=len(turmas_ativas),
        vagas_ocupadas=vagas_ocupadas,
        capacidade_total=capacidade_total,
        taxa_ocupacao_geral_percentual=taxa_ocupacao,
        ticket_medio=ticket_medio,
        ponto_equilibrio_alunos=ponto_equilibrio_alunos,
        ponto_equilibrio_valor=despesas_previstas_mes,
        receita_esperada_mes=receita_esperada_mes,
        receita_recebida_mes=receita_recebida_mes,
        percentual_recebido_mes=percentual_recebido_mes,
        despesas_previstas_mes=despesas_previstas_mes,
        despesas_pagas_mes=despesas_pagas_mes,
        lucro_mes=lucro_mes,
        lucro_acumulado=lucro_acumulado,
        despesas_atrasadas_qtd=despesas_atrasadas_qtd,
        despesas_atrasadas_valor=despesas_atrasadas_valor,
        total_faturas_abertas=faturas_abertas,
        total_inadimplentes=total_inadimplentes,
        valor_total_inadimplente=valor_inadimplente
    )


@router.get("/room-occupancy", response_model=List[RoomOccupancyReport], summary="Relatório de ocupação de salas")
def get_room_occupancy_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    salas = db.query(Room).filter(Room.ativa.is_(True)).all()
    relatorio = []

    for s in salas:
        turmas_na_sala = db.query(ClassGroup).filter(
            ClassGroup.sala_id == s.id,
            ClassGroup.ativa.is_(True)
        ).all()

        detalhes_turmas = []
        total_vagas_ocupadas = 0
        for t in turmas_na_sala:
            ocupados = contar_matriculas_ativas(db, t.id)
            total_vagas_ocupadas += ocupados
            detalhes_turmas.append({
                "turma_id": t.id,
                "turma_nome": t.nome,
                "dia_semana": t.dia_semana,
                "horario": f"{t.horario_inicio}-{t.horario_fim}",
                "alunos_matriculados": ocupados,
                "capacidade_maxima": t.capacidade_maxima,
                "ocupacao_percentual": round((ocupados / t.capacidade_maxima) * 100, 1)
            })

        cap_total_sala = len(turmas_na_sala) * s.capacidade if turmas_na_sala else s.capacidade
        taxa_media = round((total_vagas_ocupadas / cap_total_sala) * 100, 1) if turmas_na_sala else 0.0

        relatorio.append(RoomOccupancyReport(
            sala_nome=s.nome,
            capacidade_sala=s.capacidade,
            turmas=detalhes_turmas,
            ocupacao_media_sala_percentual=taxa_media
        ))

    return relatorio


@router.get("/export/students-csv", summary="Exportar cadastro de alunos em CSV")
def export_students_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.SECRETARIA.value))
):
    alunos = db.query(Aluno).options(joinedload(Aluno.responsavel)).order_by(Aluno.nome.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "ID", "Nome do Aluno", "Data Nascimento", "CPF Aluno", "Telefone",
        "E-mail", "Possui Responsável", "Nome Responsável", "CPF Responsável",
        "Telefone Responsável", "E-mail Responsável", "Autorização Imagem", "Status"
    ])

    for a in alunos:
        tem_resp = "SIM" if a.responsavel else "NÃO"
        resp_nome = a.responsavel.nome if a.responsavel else ""
        resp_cpf = a.responsavel.cpf if a.responsavel else ""
        resp_tel = a.responsavel.telefone if a.responsavel else ""
        resp_email = a.responsavel.email if a.responsavel else ""
        status_txt = "ATIVO" if a.ativo else "INATIVO"
        imagem_txt = "SIM" if a.autorizacao_imagem else "NÃO"

        writer.writerow([
            a.id, a.nome, a.data_nascimento.strftime("%d/%m/%Y"), a.cpf or "",
            a.telefone or "", a.email or "", tem_resp, resp_nome, resp_cpf,
            resp_tel, resp_email, imagem_txt, status_txt
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alunos_helena_barufaldi.csv"}
    )


@router.get("/export/invoices-csv", summary="Exportar títulos financeiros em CSV")
def export_invoices_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.FINANCEIRO.value))
):
    invoices = db.query(Invoice).options(
        joinedload(Invoice.aluno),
        joinedload(Invoice.responsavel)
    ).order_by(Invoice.data_vencimento.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "ID", "Descrição", "Competência", "Aluno", "Responsável Financeiro",
        "Valor Nominal", "Desconto Concedido", "Multa/Juros", "Valor Final",
        "Data Vencimento", "Status", "Forma Pagamento", "Data Pagamento"
    ])

    for inv in invoices:
        aluno_nome = inv.aluno.nome if inv.aluno else ""
        resp_nome = inv.responsavel.nome if inv.responsavel else ""
        data_pag = inv.data_pagamento.strftime("%d/%m/%Y %H:%M") if inv.data_pagamento else ""

        writer.writerow([
            inv.id, inv.descricao, inv.competencia, aluno_nome, resp_nome,
            f"{inv.valor_nominal:.2f}", f"{inv.desconto_aplicado:.2f}",
            f"{inv.juros_multa:.2f}", f"{inv.valor_final:.2f}",
            inv.data_vencimento.strftime("%d/%m/%Y"), inv.status,
            inv.forma_pagamento or "", data_pag
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financeiro_helena_barufaldi.csv"}
    )
