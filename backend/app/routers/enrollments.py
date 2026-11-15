from datetime import date, datetime, timezone
from typing import List, Optional
import uuid
import calendar
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.enrollment import Matricula, StatusMatricula
from app.models.financial import Invoice, StatusTitulo
from app.models.waitlist import ListaEspera
from app.models.student import Aluno
from app.models.class_group import ClassGroup
from app.models.user import User, UserRole
from app.schemas.enrollment import (
    MatriculaCreate, MatriculaUpdate, MatriculaResponse,
    ListaEsperaCreate, ListaEsperaResponse
)
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/enrollments", tags=["Matrículas e Lista de Espera"])


def contar_matriculas_ativas(db: Session, turma_id: int) -> int:
    """Conta alunos matriculados e ativos (excluindo experimentais cancelados) em uma turma."""
    return db.query(Matricula).filter(
        Matricula.turma_id == turma_id,
        Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value])
    ).count()


def contar_parcelas_matricula(db: Session, matricula_id: int) -> int:
    """Conta títulos não cancelados vinculados a uma matrícula."""
    return db.query(Invoice).filter(
        Invoice.matricula_id == matricula_id,
        Invoice.status != StatusTitulo.CANCELADO.value
    ).count()


def gerar_faturas_matricula(
    db: Session,
    matricula: Matricula,
    aluno: Optional[Aluno] = None,
    turma: Optional[ClassGroup] = None
) -> List[Invoice]:
    """
    Gera as mensalidades faltantes (até quantidade_parcelas) para uma matrícula ativa
    não experimental, evitando duplicidade por competência (YYYY-MM).
    """
    if matricula.status != StatusMatricula.ATIVA.value or matricula.aula_experimental:
        return []

    quantidade_parcelas = matricula.quantidade_parcelas if matricula.quantidade_parcelas is not None else 12
    dia_vencimento = matricula.dia_vencimento or 10
    if quantidade_parcelas <= 0:
        return []

    if aluno is None:
        aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(Aluno.id == matricula.aluno_id).first()
    if turma is None:
        turma = db.query(ClassGroup).filter(ClassGroup.id == matricula.turma_id).first()

    faturas_existentes = db.query(Invoice).filter(
        Invoice.matricula_id == matricula.id,
        Invoice.status != StatusTitulo.CANCELADO.value
    ).all()

    if len(faturas_existentes) >= quantidade_parcelas:
        return []

    competencias_existentes = {inv.competencia for inv in faturas_existentes}

    ano_cursor = matricula.data_inicio.year
    mes_cursor = matricula.data_inicio.month
    hoje = date.today()
    valor_nominal = round(float(matricula.valor_mensalidade or 0.0), 2)
    desconto_pct = float(matricula.desconto_percentual or 0.0)
    desconto_val = round(valor_nominal * (desconto_pct / 100), 2)
    valor_final = round(max(0.0, valor_nominal - desconto_val), 2)
    resp_id = aluno.responsavel.id if aluno and aluno.responsavel else None
    turma_nome = turma.nome if turma else f"Turma #{matricula.turma_id}"

    novas_faturas: List[Invoice] = []
    for i in range(quantidade_parcelas):
        max_dias = calendar.monthrange(ano_cursor, mes_cursor)[1]
        dia_efetivo = min(dia_vencimento, max_dias)
        data_venc = date(ano_cursor, mes_cursor, dia_efetivo)
        competencia = f"{ano_cursor:04d}-{mes_cursor:02d}"

        mes_atual = mes_cursor
        ano_atual = ano_cursor
        mes_cursor += 1
        if mes_cursor > 12:
            mes_cursor = 1
            ano_cursor += 1

        if competencia in competencias_existentes:
            continue

        status_inv = StatusTitulo.ATRASADO.value if data_venc < hoje else StatusTitulo.PENDENTE.value
        desc = f"Mensalidade {i+1}/{quantidade_parcelas} ({mes_atual:02d}/{ano_atual}) - {turma_nome}"[:200]

        fatura = Invoice(
            matricula_id=matricula.id,
            aluno_id=matricula.aluno_id,
            responsavel_id=resp_id,
            descricao=desc,
            competencia=competencia,
            valor_nominal=valor_nominal,
            desconto_aplicado=desconto_val,
            valor_final=valor_final,
            data_vencimento=data_venc,
            status=status_inv
        )
        db.add(fatura)
        novas_faturas.append(fatura)
        competencias_existentes.add(competencia)

    return novas_faturas


def formatar_matricula_response(matricula: Matricula, total_parcelas: int = 0) -> MatriculaResponse:
    resp = MatriculaResponse.model_validate(matricula)
    if matricula.aluno:
        resp.aluno_nome = matricula.aluno.nome
    if matricula.turma:
        resp.turma_nome = matricula.turma.nome
    if matricula.desconto_percentual and matricula.valor_mensalidade:
        resp.valor_com_desconto = round(
            matricula.valor_mensalidade * (1 - matricula.desconto_percentual / 100), 2
        )
    resp.total_parcelas_geradas = total_parcelas
    return resp


@router.get("/", response_model=List[MatriculaResponse], summary="Listar matrículas")
def list_enrollments(
    aluno_id: Optional[int] = Query(None, description="Filtrar por aluno"),
    turma_id: Optional[int] = Query(None, description="Filtrar por turma"),
    status_filter: Optional[StatusMatricula] = Query(None, alias="status", description="Filtrar por status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Matricula).options(joinedload(Matricula.aluno), joinedload(Matricula.turma))
    if aluno_id:
        query = query.filter(Matricula.aluno_id == aluno_id)
    if turma_id:
        query = query.filter(Matricula.turma_id == turma_id)
    if status_filter:
        query = query.filter(Matricula.status == status_filter.value)

    matriculas = query.order_by(Matricula.data_matricula.desc()).all()
    contagem_rows = db.query(
        Invoice.matricula_id, func.count(Invoice.id)
    ).filter(
        Invoice.status != StatusTitulo.CANCELADO.value
    ).group_by(Invoice.matricula_id).all()
    contagem_map = {mat_id: total for mat_id, total in contagem_rows}

    return [formatar_matricula_response(m, total_parcelas=contagem_map.get(m.id, 0)) for m in matriculas]


@router.post(
    "/",
    response_model=MatriculaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Realizar matrícula de aluno em turma"
)
def create_enrollment(
    mat_in: MatriculaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    """
    Realiza a matrícula de um aluno. Regras aplicadas:
    - Turma deve ter vagas (máx. 9 alunos ativos)
    - Aluno não pode estar já matriculado e ativo na mesma turma
    - Matrícula cria número de contrato único (renovação NÃO é automática)
    """
    client_ip = request.client.host if request.client else None

    # 1. Valida existência do aluno
    aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(
        Aluno.id == mat_in.aluno_id, Aluno.ativo.is_(True)
    ).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ativo não encontrado.")

    # 2. Valida existência e atividade da turma
    turma = db.query(ClassGroup).filter(
        ClassGroup.id == mat_in.turma_id, ClassGroup.ativa.is_(True)
    ).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma ativa não encontrada.")

    # 3. Verifica se aluno já está matriculado na turma
    matricula_existente = db.query(Matricula).filter(
        Matricula.aluno_id == mat_in.aluno_id,
        Matricula.turma_id == mat_in.turma_id,
        Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value])
    ).first()
    if matricula_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este aluno já possui matrícula ativa nesta turma."
        )

    # 4. Verifica capacidade (regra estrita: máx. 9 alunos)
    vagas_ocupadas = contar_matriculas_ativas(db, mat_in.turma_id)
    if vagas_ocupadas >= turma.capacidade_maxima:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A turma '{turma.nome}' está com capacidade máxima atingida "
                f"({vagas_ocupadas}/{turma.capacidade_maxima} alunos). "
                "Use a lista de espera para registrar o interesse do aluno."
            )
        )

    # 5. Gera número de contrato único
    numero_contrato = f"MAT-{date.today().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"

    status_inicial = StatusMatricula.EXPERIMENTAL.value if mat_in.aula_experimental else StatusMatricula.ATIVA.value

    dia_vencimento = mat_in.dia_vencimento or 10
    quantidade_parcelas = mat_in.quantidade_parcelas if mat_in.quantidade_parcelas is not None else 12

    nova_matricula = Matricula(
        aluno_id=mat_in.aluno_id,
        turma_id=mat_in.turma_id,
        status=status_inicial,
        data_matricula=mat_in.data_matricula,
        data_inicio=mat_in.data_inicio,
        data_termino_previsto=mat_in.data_termino_previsto,
        numero_contrato=numero_contrato,
        contrato_assinado=False,  # sempre inicia pendente de assinatura
        valor_mensalidade=mat_in.valor_mensalidade,
        desconto_percentual=mat_in.desconto_percentual,
        tipo_desconto=mat_in.tipo_desconto,
        dia_vencimento=dia_vencimento,
        quantidade_parcelas=quantidade_parcelas,
        aula_experimental=mat_in.aula_experimental,
        observacoes=mat_in.observacoes
    )
    db.add(nova_matricula)
    db.flush()

    # Gerar todas as faturas/mensalidades se não for aula experimental
    faturas_geradas = gerar_faturas_matricula(db, nova_matricula, aluno=aluno, turma=turma)

    db.commit()
    db.refresh(nova_matricula)

    registrar_auditoria(
        db=db,
        acao="MATRICULA_CRIADA",
        entidade="Matricula",
        registro_id=str(nova_matricula.id),
        detalhes={
            "aluno": aluno.nome,
            "turma": turma.nome,
            "contrato": numero_contrato,
            "experimental": mat_in.aula_experimental,
            "desconto": mat_in.desconto_percentual,
            "tipo_desconto": mat_in.tipo_desconto,
            "parcelas_geradas": len(faturas_geradas)
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(nova_matricula, total_parcelas=len(faturas_geradas))


@router.get("/{matricula_id}", response_model=MatriculaResponse, summary="Obter dados da matrícula")
def get_enrollment(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno), joinedload(Matricula.turma)
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")
    return formatar_matricula_response(matricula, total_parcelas=contar_parcelas_matricula(db, matricula.id))


@router.put("/{matricula_id}", response_model=MatriculaResponse, summary="Atualizar matrícula (status, contrato, descontos)")
def update_enrollment(
    matricula_id: int,
    mat_update: MatriculaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.FINANCEIRO.value
    ))
):
    """
    Atualiza a matrícula.
    - Renovação: precisa ser feita manualmente com novo contrato assinado (NÃO automática).
    - Cancelamento/Trancamento: registra motivo e multa conforme contrato.
    - Se a matrícula passar para ATIVA (não experimental), gera automaticamente as parcelas faltantes.
    """
    client_ip = request.client.host if request.client else None
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma)
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    if mat_update.status is not None:
        # Validação do fluxo de status
        if mat_update.status == StatusMatricula.CANCELADA:
            if not mat_update.motivo_cancelamento:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Para cancelamento de matrícula é obrigatório informar o motivo."
                )
            matricula.motivo_cancelamento = mat_update.motivo_cancelamento
            matricula.data_cancelamento = datetime.now(timezone.utc)
            matricula.multa_cancelamento = mat_update.multa_cancelamento or 0.0
        matricula.status = mat_update.status.value
        if mat_update.status == StatusMatricula.ATIVA and mat_update.aula_experimental is None:
            matricula.aula_experimental = False
        elif mat_update.status == StatusMatricula.EXPERIMENTAL and mat_update.aula_experimental is None:
            matricula.aula_experimental = True

    if mat_update.aula_experimental is not None:
        matricula.aula_experimental = mat_update.aula_experimental

    if mat_update.contrato_assinado is not None:
        matricula.contrato_assinado = mat_update.contrato_assinado
        if mat_update.contrato_assinado:
            matricula.data_assinatura_contrato = datetime.now(timezone.utc)

    if mat_update.valor_mensalidade is not None:
        matricula.valor_mensalidade = mat_update.valor_mensalidade
    if mat_update.dia_vencimento is not None:
        matricula.dia_vencimento = mat_update.dia_vencimento
    if mat_update.quantidade_parcelas is not None:
        matricula.quantidade_parcelas = mat_update.quantidade_parcelas
    if mat_update.desconto_percentual is not None:
        matricula.desconto_percentual = mat_update.desconto_percentual
    if mat_update.tipo_desconto is not None:
        matricula.tipo_desconto = mat_update.tipo_desconto
    if mat_update.observacoes is not None:
        matricula.observacoes = mat_update.observacoes

    faturas_geradas = gerar_faturas_matricula(
        db, matricula, aluno=matricula.aluno, turma=matricula.turma
    )

    db.commit()
    db.refresh(matricula)
    total_parcelas = contar_parcelas_matricula(db, matricula.id)

    registrar_auditoria(
        db=db,
        acao="MATRICULA_ATUALIZADA",
        entidade="Matricula",
        registro_id=str(matricula.id),
        detalhes={
            "status": matricula.status,
            "contrato_assinado": matricula.contrato_assinado,
            "parcelas_geradas": len(faturas_geradas)
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(matricula, total_parcelas=total_parcelas)


@router.post(
    "/{matricula_id}/generate-invoices",
    summary="Gerar parcelas faltantes de uma matrícula ativa"
)
def generate_enrollment_invoices(
    matricula_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.FINANCEIRO.value
    ))
):
    """Gera mensalidades/parcelas pendentes para uma matrícula ativa que ainda não possua todas as parcelas."""
    client_ip = request.client.host if request.client else None
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno).joinedload(Aluno.responsavel),
        joinedload(Matricula.turma)
    ).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")

    if matricula.status in [StatusMatricula.CANCELADA.value, StatusMatricula.TRANCADA.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula cancelada ou trancada não pode gerar novas faturas."
        )

    if matricula.status == StatusMatricula.EXPERIMENTAL.value or matricula.aula_experimental:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula experimental não gera cobrança financeira. Edite o status para ATIVA antes de gerar parcelas."
        )

    novas = gerar_faturas_matricula(db, matricula, aluno=matricula.aluno, turma=matricula.turma)
    db.commit()
    total_parcelas = contar_parcelas_matricula(db, matricula.id)

    if novas:
        registrar_auditoria(
            db=db,
            acao="PARCELAS_MATRICULA_GERADAS",
            entidade="Matricula",
            registro_id=str(matricula.id),
            detalhes={"parcelas_geradas": len(novas), "total_parcelas": total_parcelas},
            usuario=current_user,
            ip=client_ip
        )

    return {
        "matricula_id": matricula.id,
        "parcelas_geradas": len(novas),
        "total_parcelas": total_parcelas,
        "mensagem": (
            f"{len(novas)} parcela(s) gerada(s) com sucesso!"
            if novas else
            "Todas as parcelas desta matrícula já estão geradas no Financeiro."
        )
    }


# ─── Lista de Espera ──────────────────────────────────────────────────────────

@router.post(
    "/waitlist",
    response_model=ListaEsperaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar aluno à lista de espera de uma turma"
)
def add_to_waitlist(
    espera_in: ListaEsperaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    aluno = db.query(Aluno).filter(Aluno.id == espera_in.aluno_id, Aluno.ativo.is_(True)).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno ativo não encontrado.")

    turma = db.query(ClassGroup).filter(ClassGroup.id == espera_in.turma_id, ClassGroup.ativa.is_(True)).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma ativa não encontrada.")

    # Verifica se aluno já está na lista de espera desta turma
    ja_na_fila = db.query(ListaEspera).filter(
        ListaEspera.aluno_id == espera_in.aluno_id,
        ListaEspera.turma_id == espera_in.turma_id,
        ListaEspera.ativa.is_(True)
    ).first()
    if ja_na_fila:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Aluno já está na lista de espera da turma '{turma.nome}' (posição {ja_na_fila.posicao})."
        )

    # Determina próxima posição na fila
    ultima_posicao = db.query(ListaEspera).filter(
        ListaEspera.turma_id == espera_in.turma_id,
        ListaEspera.ativa.is_(True)
    ).count()

    nova_entrada = ListaEspera(
        aluno_id=espera_in.aluno_id,
        turma_id=espera_in.turma_id,
        posicao=ultima_posicao + 1,
        ativa=True,
        notificado=False,
        observacoes=espera_in.observacoes
    )
    db.add(nova_entrada)
    db.commit()
    db.refresh(nova_entrada)

    resp = ListaEsperaResponse.model_validate(nova_entrada)
    resp.aluno_nome = aluno.nome
    resp.turma_nome = turma.nome
    return resp


@router.get(
    "/waitlist/{turma_id}",
    response_model=List[ListaEsperaResponse],
    summary="Listar fila de espera de uma turma"
)
def get_waitlist(
    turma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    entradas = db.query(ListaEspera).options(
        joinedload(ListaEspera.aluno), joinedload(ListaEspera.turma)
    ).filter(
        ListaEspera.turma_id == turma_id,
        ListaEspera.ativa.is_(True)
    ).order_by(ListaEspera.posicao.asc()).all()

    result = []
    for e in entradas:
        resp = ListaEsperaResponse.model_validate(e)
        if e.aluno:
            resp.aluno_nome = e.aluno.nome
        if e.turma:
            resp.turma_nome = e.turma.nome
        result.append(resp)
    return result
