from datetime import date, datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.enrollment import Matricula, StatusMatricula
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


def formatar_matricula_response(matricula: Matricula) -> MatriculaResponse:
    resp = MatriculaResponse.model_validate(matricula)
    if matricula.aluno:
        resp.aluno_nome = matricula.aluno.nome
    if matricula.turma:
        resp.turma_nome = matricula.turma.nome
    if matricula.desconto_percentual and matricula.valor_mensalidade:
        resp.valor_com_desconto = round(
            matricula.valor_mensalidade * (1 - matricula.desconto_percentual / 100), 2
        )
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
    return [formatar_matricula_response(m) for m in query.order_by(Matricula.data_matricula.desc()).all()]


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
    aluno = db.query(Aluno).filter(Aluno.id == mat_in.aluno_id, Aluno.ativo.is_(True)).first()
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
        aula_experimental=mat_in.aula_experimental,
        observacoes=mat_in.observacoes
    )
    db.add(nova_matricula)
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
            "tipo_desconto": mat_in.tipo_desconto
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(nova_matricula)


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
    return formatar_matricula_response(matricula)


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
    """
    client_ip = request.client.host if request.client else None
    matricula = db.query(Matricula).options(
        joinedload(Matricula.aluno), joinedload(Matricula.turma)
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

    if mat_update.contrato_assinado is not None:
        matricula.contrato_assinado = mat_update.contrato_assinado
        if mat_update.contrato_assinado:
            matricula.data_assinatura_contrato = datetime.now(timezone.utc)

    if mat_update.desconto_percentual is not None:
        matricula.desconto_percentual = mat_update.desconto_percentual
    if mat_update.tipo_desconto is not None:
        matricula.tipo_desconto = mat_update.tipo_desconto
    if mat_update.observacoes is not None:
        matricula.observacoes = mat_update.observacoes

    db.commit()
    db.refresh(matricula)

    registrar_auditoria(
        db=db,
        acao="MATRICULA_ATUALIZADA",
        entidade="Matricula",
        registro_id=str(matricula.id),
        detalhes={"status": matricula.status, "contrato_assinado": matricula.contrato_assinado},
        usuario=current_user,
        ip=client_ip
    )
    return formatar_matricula_response(matricula)


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
