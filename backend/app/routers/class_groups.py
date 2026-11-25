from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.enrollment import Matricula
from app.models.attendance import Lesson, ClassMakeUp, Evaluation
from app.models.user import User, UserRole
from app.schemas.class_group import ClassGroupCreate, ClassGroupUpdate, ClassGroupResponse, CourseResumo
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/classes", tags=["Turmas e Horários"])


def _resolver_cursos_ativos(db: Session, cursos_ids: List[int]) -> List[Course]:
    """Valida e retorna os cursos ativos na ordem informada."""
    cursos = db.query(Course).filter(Course.id.in_(cursos_ids), Course.ativo.is_(True)).all()
    cursos_map = {c.id: c for c in cursos}
    faltantes = [cid for cid in cursos_ids if cid not in cursos_map]
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uma ou mais modalidades artísticas ativas não foram encontradas."
        )
    return [cursos_map[cid] for cid in cursos_ids]


def formatar_turma_response(turma: ClassGroup) -> ClassGroupResponse:
    cursos_lista = list(turma.cursos or [])
    if not cursos_lista and turma.curso:
        cursos_lista = [turma.curso]

    resp = ClassGroupResponse.model_validate(turma)
    resp.cursos = [CourseResumo.model_validate(c) for c in cursos_lista]
    resp.cursos_ids = [c.id for c in cursos_lista]
    resp.cursos_nomes = [c.nome for c in cursos_lista]
    if cursos_lista:
        resp.curso_id = cursos_lista[0].id
        resp.curso_nome = ", ".join(c.nome for c in cursos_lista)
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
    query = db.query(ClassGroup).options(
        joinedload(ClassGroup.cursos),
        joinedload(ClassGroup.curso),
        joinedload(ClassGroup.sala),
        joinedload(ClassGroup.professor),
    )
    if apenas_ativas:
        query = query.filter(ClassGroup.ativa.is_(True))
    if dia_semana:
        query = query.filter(ClassGroup.dia_semana == dia_semana.value)
    if faixa_etaria:
        query = query.filter(ClassGroup.faixa_etaria == faixa_etaria.value)
    if curso_id:
        query = query.filter(
            or_(
                ClassGroup.curso_id == curso_id,
                ClassGroup.cursos.any(Course.id == curso_id)
            )
        )
    if sala_id:
        query = query.filter(ClassGroup.sala_id == sala_id)
    if professor_id:
        query = query.filter(ClassGroup.professor_id == professor_id)

    # Professores têm acesso apenas às próprias turmas
    if current_user.role == UserRole.PROFESSOR.value:
        prof = db.query(Teacher).filter(
            (Teacher.user_id == current_user.id) | (Teacher.email == current_user.email)
        ).first()
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
    """Cria uma nova turma (incluindo turmas mistas com múltiplos cursos e capacidade configurável por sala)."""
    # 1. Valida existência dos cursos associados
    cursos = _resolver_cursos_ativos(db, turma_in.cursos_ids)

    # 2. Valida existência da sala e capacidade configurável
    sala = db.query(Room).filter(Room.id == turma_in.sala_id).first()
    if not sala or not sala.ativa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala ativa não encontrada.")

    capacidade_turma = turma_in.capacidade_maxima if turma_in.capacidade_maxima is not None else sala.capacidade
    if capacidade_turma > sala.capacidade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A capacidade da turma ({capacidade_turma}) não pode ser maior que a da sala ({sala.capacidade})."
        )

    # 3. Valida existência do professor
    professor = db.query(Teacher).filter(Teacher.id == turma_in.professor_id).first()
    if not professor or not professor.ativo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor ativo não encontrado.")

    nova_turma = ClassGroup(
        nome=turma_in.nome.strip(),
        curso_id=cursos[0].id,
        sala_id=turma_in.sala_id,
        professor_id=turma_in.professor_id,
        faixa_etaria=turma_in.faixa_etaria.value,
        dia_semana=turma_in.dia_semana.value,
        turno=turma_in.turno.value,
        horario_inicio=turma_in.horario_inicio,
        horario_fim=turma_in.horario_fim,
        capacidade_maxima=capacidade_turma,
        ativa=True
    )
    nova_turma.cursos = cursos

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
            "cursos": [c.nome for c in cursos],
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
    turma = db.query(ClassGroup).options(
        joinedload(ClassGroup.cursos),
        joinedload(ClassGroup.curso),
        joinedload(ClassGroup.sala),
        joinedload(ClassGroup.professor),
    ).filter(ClassGroup.id == turma_id).first()
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
    turma = db.query(ClassGroup).options(joinedload(ClassGroup.cursos)).filter(ClassGroup.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    sala_id = turma_update.sala_id if turma_update.sala_id is not None else turma.sala_id
    horario_inicio = turma_update.horario_inicio if turma_update.horario_inicio is not None else turma.horario_inicio
    horario_fim = turma_update.horario_fim if turma_update.horario_fim is not None else turma.horario_fim

    if horario_inicio >= horario_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Horário de início deve ser menor que o de término."
        )

    sala = db.query(Room).filter(Room.id == sala_id).first()
    if not sala or (turma_update.sala_id is not None and not sala.ativa):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala ativa não encontrada.")

    if turma_update.professor_id is not None:
        professor = db.query(Teacher).filter(Teacher.id == turma_update.professor_id).first()
        if not professor or not professor.ativo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor ativo não encontrado.")

    capacidade_efetiva = (
        turma_update.capacidade_maxima
        if turma_update.capacidade_maxima is not None
        else turma.capacidade_maxima
    )
    if capacidade_efetiva > sala.capacidade:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A capacidade da turma ({capacidade_efetiva}) não pode exceder a capacidade da sala ({sala.capacidade})."
        )

    cursos_novos_ids: Optional[List[int]] = None
    if turma_update.cursos_ids is not None:
        cursos_novos_ids = turma_update.cursos_ids
    elif turma_update.curso_id is not None:
        cursos_novos_ids = [turma_update.curso_id]

    if cursos_novos_ids is not None:
        cursos = _resolver_cursos_ativos(db, cursos_novos_ids)
        turma.cursos = cursos
        turma.curso_id = cursos[0].id

    if turma_update.capacidade_maxima is not None:
        turma.capacidade_maxima = turma_update.capacidade_maxima
    if turma_update.nome is not None:
        turma.nome = turma_update.nome.strip()
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
        detalhes={"nome": turma.nome, "ativa": turma.ativa, "capacidade": turma.capacidade_maxima},
        usuario=current_user,
        ip=client_ip
    )
    return formatar_turma_response(turma)


@router.delete("/{turma_id}", status_code=status.HTTP_200_OK, summary="Excluir ou desativar turma")
def delete_class_group(
    turma_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    turma = db.query(ClassGroup).filter(ClassGroup.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    has_links = (
        db.query(Matricula).filter(Matricula.turma_id == turma_id).count()
        + db.query(Lesson).filter(Lesson.turma_id == turma_id).count()
        + db.query(ClassMakeUp).filter(ClassMakeUp.turma_destino_id == turma_id).count()
        + db.query(Evaluation).filter(Evaluation.turma_id == turma_id).count()
    )

    if has_links > 0:
        turma.ativa = False
        db.commit()
        db.refresh(turma)
        msg = f"Turma '{turma.nome}' possui matrículas ou registros vinculados e foi desativada com sucesso."
    else:
        db.delete(turma)
        db.commit()
        msg = f"Turma '{turma.nome}' excluída com sucesso."

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="TURMA_EXCLUIDA",
        entidade="ClassGroup",
        registro_id=str(turma_id),
        detalhes={"acao": msg},
        usuario=current_user,
        ip=client_ip
    )
    return {"status": "ok", "mensagem": msg}
