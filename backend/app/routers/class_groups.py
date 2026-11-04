from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.class_group import ClassGroupCreate, ClassGroupUpdate, ClassGroupResponse
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/classes", tags=["Turmas e Horários"])


def verificar_sobreposicao_horario(inicio_a: str, fim_a: str, inicio_b: str, fim_b: str) -> bool:
    """Verifica se dois intervalos de horário (formato HH:MM) se sobrepõem."""
    return inicio_a < fim_b and fim_a > inicio_b


def validar_conflitos(
    db: Session,
    sala_id: int,
    professor_id: int,
    dia_semana: str,
    horario_inicio: str,
    horario_fim: str,
    turma_id_ignorar: Optional[int] = None
):
    """
    Verifica se há conflitos de agendamento:
    1. Sala já ocupada no mesmo dia e intervalo de horário.
    2. Professor já alocado em outra turma no mesmo dia e intervalo de horário.
    """
    # Turmas ativas no mesmo dia da semana
    query = db.query(ClassGroup).filter(
        ClassGroup.dia_semana == dia_semana,
        ClassGroup.ativa.is_(True)
    )
    if turma_id_ignorar is not None:
        query = query.filter(ClassGroup.id != turma_id_ignorar)

    turmas_no_dia = query.all()

    for turma in turmas_no_dia:
        if verificar_sobreposicao_horario(horario_inicio, horario_fim, turma.horario_inicio, turma.horario_fim):
            if turma.sala_id == sala_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Conflito de sala: A sala já está reservada para a turma '{turma.nome}' "
                        f"no horário {turma.horario_inicio} às {turma.horario_fim} ({dia_semana})."
                    )
                )
            if turma.professor_id == professor_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Conflito de professor: O professor já está alocado na turma '{turma.nome}' "
                        f"no horário {turma.horario_inicio} às {turma.horario_fim} ({dia_semana})."
                    )
                )


def formatar_turma_response(turma: ClassGroup) -> ClassGroupResponse:
    resp = ClassGroupResponse.model_validate(turma)
    if turma.curso:
        resp.curso_nome = turma.curso.nome
    if turma.sala:
        resp.sala_nome = turma.sala.nome
    if turma.professor:
        resp.professor_nome = turma.professor.nome
    return resp


@router.get("/", response_model=List[ClassGroupResponse], summary="Listar turmas")
def list_class_groups(
    apenas_ativas: bool = Query(True, description="Filtrar turmas ativas"),
    dia_semana: Optional[DiaSemana] = Query(None, description="Filtrar por dia da semana"),
    faixa_etaria: Optional[FaixaEtaria] = Query(None, description="Filtrar por faixa etária"),
    curso_id: Optional[int] = Query(None, description="Filtrar por modalidade artística"),
    sala_id: Optional[int] = Query(None, description="Filtrar por sala"),
    professor_id: Optional[int] = Query(None, description="Filtrar por professor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(ClassGroup)
    if apenas_ativas:
        query = query.filter(ClassGroup.ativa.is_(True))
    if dia_semana:
        query = query.filter(ClassGroup.dia_semana == dia_semana.value)
    if faixa_etaria:
        query = query.filter(ClassGroup.faixa_etaria == faixa_etaria.value)
    if curso_id:
        query = query.filter(ClassGroup.curso_id == curso_id)
    if sala_id:
        query = query.filter(ClassGroup.sala_id == sala_id)
    if professor_id:
        query = query.filter(ClassGroup.professor_id == professor_id)

    # Professores têm acesso apenas às próprias turmas
    if current_user.role == UserRole.PROFESSOR.value:
        prof = db.query(Teacher).filter((Teacher.user_id == current_user.id) | (Teacher.email == current_user.email)).first()
        if prof:
            query = query.filter(ClassGroup.professor_id == prof.id)
        else:
            return []

    turmas = query.order_by(ClassGroup.dia_semana.asc(), ClassGroup.horario_inicio.asc()).all()
    return [formatar_turma_response(t) for t in turmas]


@router.post(
    "/",
    response_model=ClassGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar nova turma"
)
def create_class_group(
    turma_in: ClassGroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    """Cria uma nova turma aplicando o limite máximo estrito de 9 alunos e prevenindo choques de horário."""
    # 1. Valida existência do curso
    curso = db.query(Course).filter(Course.id == turma_in.curso_id).first()
    if not curso or not curso.ativo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalidade artística ativa não encontrada.")

    # 2. Valida existência da sala e capacidade máxima
    sala = db.query(Room).filter(Room.id == turma_in.sala_id).first()
    if not sala or not sala.ativa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala ativa não encontrada.")

    if turma_in.capacidade_maxima > 9:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A capacidade máxima de uma turma não pode exceder 9 alunos (regra da Escola Helena Barufaldi)."
        )

    if turma_in.capacidade_maxima > sala.capacidade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A capacidade da turma ({turma_in.capacidade_maxima}) não pode ser maior que a da sala ({sala.capacidade})."
        )

    # 3. Valida existência do professor
    professor = db.query(Teacher).filter(Teacher.id == turma_in.professor_id).first()
    if not professor or not professor.ativo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor ativo não encontrado.")

    # 4. Validação anti-conflito
    validar_conflitos(
        db=db,
        sala_id=turma_in.sala_id,
        professor_id=turma_in.professor_id,
        dia_semana=turma_in.dia_semana.value,
        horario_inicio=turma_in.horario_inicio,
        horario_fim=turma_in.horario_fim
    )

    nova_turma = ClassGroup(
        nome=turma_in.nome.strip(),
        curso_id=turma_in.curso_id,
        sala_id=turma_in.sala_id,
        professor_id=turma_in.professor_id,
        faixa_etaria=turma_in.faixa_etaria.value,
        dia_semana=turma_in.dia_semana.value,
        turno=turma_in.turno.value,
        horario_inicio=turma_in.horario_inicio,
        horario_fim=turma_in.horario_fim,
        capacidade_maxima=turma_in.capacidade_maxima,
        ativa=True
    )
    db.add(nova_turma)
    db.commit()
    db.refresh(nova_turma)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="TURMA_CRIADA",
        entidade="ClassGroup",
        registro_id=str(nova_turma.id),
        detalhes={
            "nome": nova_turma.nome,
            "curso": curso.nome,
            "sala": sala.nome,
            "professor": professor.nome,
            "dia": nova_turma.dia_semana,
            "horario": f"{nova_turma.horario_inicio}-{nova_turma.horario_fim}",
            "capacidade": nova_turma.capacidade_maxima
        },
        usuario=current_user,
        ip=client_ip
    )
    return formatar_turma_response(nova_turma)


@router.get("/{turma_id}", response_model=ClassGroupResponse, summary="Obter dados de uma turma")
def get_class_group(
    turma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    turma = db.query(ClassGroup).filter(ClassGroup.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")
    return formatar_turma_response(turma)


@router.put("/{turma_id}", response_model=ClassGroupResponse, summary="Atualizar dados da turma")
def update_class_group(
    turma_id: int,
    turma_update: ClassGroupUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    turma = db.query(ClassGroup).filter(ClassGroup.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    sala_id = turma_update.sala_id if turma_update.sala_id is not None else turma.sala_id
    professor_id = turma_update.professor_id if turma_update.professor_id is not None else turma.professor_id
    dia_semana = turma_update.dia_semana.value if turma_update.dia_semana is not None else turma.dia_semana
    horario_inicio = turma_update.horario_inicio if turma_update.horario_inicio is not None else turma.horario_inicio
    horario_fim = turma_update.horario_fim if turma_update.horario_fim is not None else turma.horario_fim

    if horario_inicio >= horario_fim:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Horário de início deve ser menor que o de término.")

    # Se houve alteração de sala, professor ou horário, revalidar conflitos
    validar_conflitos(
        db=db,
        sala_id=sala_id,
        professor_id=professor_id,
        dia_semana=dia_semana,
        horario_inicio=horario_inicio,
        horario_fim=horario_fim,
        turma_id_ignorar=turma.id
    )

    if turma_update.capacidade_maxima is not None:
        if turma_update.capacidade_maxima > 9:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A capacidade máxima não pode ultrapassar 9.")
        sala = db.query(Room).filter(Room.id == sala_id).first()
        if sala and turma_update.capacidade_maxima > sala.capacidade:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Capacidade da turma não pode exceder capacidade da sala.")
        turma.capacidade_maxima = turma_update.capacidade_maxima

    if turma_update.nome is not None:
        turma.nome = turma_update.nome.strip()
    if turma_update.curso_id is not None:
        turma.curso_id = turma_update.curso_id
    if turma_update.sala_id is not None:
        turma.sala_id = turma_update.sala_id
    if turma_update.professor_id is not None:
        turma.professor_id = turma_update.professor_id
    if turma_update.faixa_etaria is not None:
        turma.faixa_etaria = turma_update.faixa_etaria.value
    if turma_update.dia_semana is not None:
        turma.dia_semana = turma_update.dia_semana.value
    if turma_update.turno is not None:
        turma.turno = turma_update.turno.value
    if turma_update.horario_inicio is not None:
        turma.horario_inicio = turma_update.horario_inicio
    if turma_update.horario_fim is not None:
        turma.horario_fim = turma_update.horario_fim
    if turma_update.ativa is not None:
        turma.ativa = turma_update.ativa

    db.commit()
    db.refresh(turma)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="TURMA_ATUALIZADA",
        entidade="ClassGroup",
        registro_id=str(turma.id),
        detalhes={"nome": turma.nome, "ativa": turma.ativa},
        usuario=current_user,
        ip=client_ip
    )
    return formatar_turma_response(turma)
