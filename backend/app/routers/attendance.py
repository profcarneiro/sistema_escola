from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.attendance import (
    Lesson, Attendance, ClassMakeUp, Evaluation,
    StatusPresenca, StatusReposicao
)
from app.models.class_group import ClassGroup
from app.models.student import Aluno
from app.models.enrollment import Matricula, StatusMatricula
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.attendance import (
    LessonCreate, LessonResponse,
    AttendanceBatchCreate, AttendanceResponse,
    ClassMakeUpCreate, ClassMakeUpResponse,
    EvaluationCreate, EvaluationResponse,
    validar_janela_reposicao,
    ClassAttendanceSummary, StudentAttendanceReport, AttendanceRecordItem
)
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/attendance", tags=["Frequência, Diário e Reposições"])


# ─── Diário de Classe (Lessons) ───────────────────────────────────────────────

@router.post(
    "/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar aula e plano de aula no Diário de Classe"
)
def create_lesson(
    lesson_in: LessonCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value
    ))
):
    """Lança o plano de aula no diário de classe para a turma."""
    turma = db.query(ClassGroup).filter(ClassGroup.id == lesson_in.turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    prof = db.query(Teacher).filter(Teacher.id == lesson_in.professor_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")

    nova_aula = Lesson(
        turma_id=lesson_in.turma_id,
        professor_id=lesson_in.professor_id,
        data_aula=lesson_in.data_aula,
        tema_aula=lesson_in.tema_aula.strip(),
        conteudo_programatico=lesson_in.conteudo_programatico,
        materiais_utilizados=lesson_in.materiais_utilizados,
        observacoes=lesson_in.observacoes
    )
    db.add(nova_aula)
    db.commit()
    db.refresh(nova_aula)

    resp = LessonResponse.model_validate(nova_aula)
    resp.turma_nome = turma.nome
    resp.professor_nome = prof.nome
    return resp


@router.get("/lessons", response_model=List[LessonResponse], summary="Listar aulas do diário de classe")
def list_lessons(
    turma_id: Optional[int] = Query(None, description="Filtrar por turma"),
    data_aula: Optional[date] = Query(None, description="Filtrar por data específica"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Lesson).options(joinedload(Lesson.turma), joinedload(Lesson.professor))
    if turma_id:
        query = query.filter(Lesson.turma_id == turma_id)
    if data_aula:
        query = query.filter(Lesson.data_aula == data_aula)

    aulas = query.order_by(Lesson.data_aula.desc()).all()
    res = []
    for a in aulas:
        r = LessonResponse.model_validate(a)
        if a.turma:
            r.turma_nome = a.turma.nome
        if a.professor:
            r.professor_nome = a.professor.nome
        res.append(r)
    return res


# ─── Chamada de Alunos (Attendance) ───────────────────────────────────────────

@router.post(
    "/lessons/{lesson_id}/batch",
    response_model=List[AttendanceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar chamada da aula"
)
def record_attendance(
    lesson_id: int,
    batch_in: AttendanceBatchCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value
    ))
):
    """Lança os status de presença dos alunos (PRESENTE, FALTA, JUSTIFICADA)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")

    registros = []
    for item in batch_in.frequencias:
        # Se já existe para este aluno nesta aula, atualiza
        existente = db.query(Attendance).filter(
            Attendance.lesson_id == lesson_id,
            Attendance.aluno_id == item.aluno_id
        ).first()

        if existente:
            existente.status = item.status.value
            existente.motivo_justificativa = item.motivo_justificativa
            registros.append(existente)
        else:
            novo = Attendance(
                lesson_id=lesson_id,
                aluno_id=item.aluno_id,
                matricula_id=item.matricula_id,
                status=item.status.value,
                motivo_justificativa=item.motivo_justificativa
            )
            db.add(novo)
            registros.append(novo)

    db.commit()

    resultado = []
    for r in registros:
        db.refresh(r)
        aluno = db.query(Aluno).filter(Aluno.id == r.aluno_id).first()
        item_resp = AttendanceResponse.model_validate(r)
        item_resp.aluno_nome = aluno.nome if aluno else None
        resultado.append(item_resp)

    return resultado


@router.get(
    "/lessons/{lesson_id}/list",
    response_model=List[AttendanceResponse],
    summary="Listar chamada de uma aula"
)
def get_lesson_attendance(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    attendances = db.query(Attendance).options(joinedload(Attendance.aluno)).filter(
        Attendance.lesson_id == lesson_id
    ).all()

    result = []
    for a in attendances:
        r = AttendanceResponse.model_validate(a)
        if a.aluno:
            r.aluno_nome = a.aluno.nome
        result.append(r)
    return result


# ─── Reposições de Aula (Makeups) ─────────────────────────────────────────────

@router.post(
    "/makeups",
    response_model=ClassMakeUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar reposição de aula"
)
def create_makeup(
    makeup_in: ClassMakeUpCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value, UserRole.PROFESSOR.value
    ))
):
    """
    Agenda reposição com validação estrita da regra do briefing:
    'Reposições feitas dentro do próprio mês ou na primeira semana do mês seguinte.'
    """
    # 1. Valida regra temporal do cliente
    try:
        validar_janela_reposicao(makeup_in.data_falta, makeup_in.data_reposicao)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # 2. Valida aluno
    aluno = db.query(Aluno).filter(Aluno.id == makeup_in.aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    # 3. Valida turma de destino
    turma_destino = db.query(ClassGroup).filter(ClassGroup.id == makeup_in.turma_destino_id).first()
    if not turma_destino or not turma_destino.ativa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma de destino não encontrada ou inativa.")

    # 4. Verifica capacidade máxima da turma de destino (teto de 9 alunos)
    from app.routers.enrollments import contar_matriculas_ativas
    matriculados_ativos = contar_matriculas_ativas(db, makeup_in.turma_destino_id)
    # Reposições ativas na mesma data e turma
    reposicoes_na_data = db.query(ClassMakeUp).filter(
        ClassMakeUp.turma_destino_id == makeup_in.turma_destino_id,
        ClassMakeUp.data_reposicao == makeup_in.data_reposicao,
        ClassMakeUp.status == StatusReposicao.AGENDADA.value
    ).count()

    if (matriculados_ativos + reposicoes_na_data) >= turma_destino.capacidade_maxima:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A turma de destino '{turma_destino.nome}' atingiu o limite de "
                f"{turma_destino.capacidade_maxima} alunos para esta data (capacidade máxima 9)."
            )
        )

    nova_reposicao = ClassMakeUp(
        aluno_id=makeup_in.aluno_id,
        matricula_origem_id=makeup_in.matricula_origem_id,
        attendance_falta_id=makeup_in.attendance_falta_id,
        data_falta=makeup_in.data_falta,
        turma_destino_id=makeup_in.turma_destino_id,
        data_reposicao=makeup_in.data_reposicao,
        status=StatusReposicao.AGENDADA.value,
        observacoes=makeup_in.observacoes
    )
    db.add(nova_reposicao)
    db.commit()
    db.refresh(nova_reposicao)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="REPOSICAO_AGENDADA",
        entidade="ClassMakeUp",
        registro_id=str(nova_reposicao.id),
        detalhes={
            "aluno": aluno.nome,
            "data_falta": str(makeup_in.data_falta),
            "data_reposicao": str(makeup_in.data_reposicao),
            "turma_destino": turma_destino.nome
        },
        usuario=current_user,
        ip=client_ip
    )

    resp = ClassMakeUpResponse.model_validate(nova_reposicao)
    resp.aluno_nome = aluno.nome
    resp.turma_destino_nome = turma_destino.nome
    return resp


@router.get("/makeups", response_model=List[ClassMakeUpResponse], summary="Listar reposições")
def list_makeups(
    aluno_id: Optional[int] = Query(None, description="Filtrar por aluno"),
    turma_destino_id: Optional[int] = Query(None, description="Filtrar por turma"),
    status_filter: Optional[StatusReposicao] = Query(None, alias="status", description="Filtrar por status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(ClassMakeUp).options(
        joinedload(ClassMakeUp.aluno), joinedload(ClassMakeUp.turma_destino)
    )
    if aluno_id:
        query = query.filter(ClassMakeUp.aluno_id == aluno_id)
    if turma_destino_id:
        query = query.filter(ClassMakeUp.turma_destino_id == turma_destino_id)
    if status_filter:
        query = query.filter(ClassMakeUp.status == status_filter.value)

    reposicoes = query.order_by(ClassMakeUp.data_reposicao.desc()).all()
    res = []
    for rep in reposicoes:
        r = ClassMakeUpResponse.model_validate(rep)
        if rep.aluno:
            r.aluno_nome = rep.aluno.nome
        if rep.turma_destino:
            r.turma_destino_nome = rep.turma_destino.nome
        res.append(r)
    return res


@router.put("/makeups/{makeup_id}/conclude", response_model=ClassMakeUpResponse, summary="Concluir reposição")
def conclude_makeup(
    makeup_id: int,
    novo_status: StatusReposicao = Query(..., description="Novo status (REALIZADA ou CANCELADA)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value
    ))
):
    makeup = db.query(ClassMakeUp).filter(ClassMakeUp.id == makeup_id).first()
    if not makeup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reposição não encontrada.")

    makeup.status = novo_status.value
    db.commit()
    db.refresh(makeup)

    resp = ClassMakeUpResponse.model_validate(makeup)
    return resp


# ─── Avaliações e Portfólio ───────────────────────────────────────────────────

@router.post(
    "/evaluations",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar avaliação pedagógica e relatório de portfólio"
)
def create_evaluation(
    eval_in: EvaluationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value
    ))
):
    aluno = db.query(Aluno).filter(Aluno.id == eval_in.aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    turma = db.query(ClassGroup).filter(ClassGroup.id == eval_in.turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    prof = db.query(Teacher).filter(Teacher.id == eval_in.professor_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")

    nova_avaliacao = Evaluation(
        aluno_id=eval_in.aluno_id,
        turma_id=eval_in.turma_id,
        professor_id=eval_in.professor_id,
        periodo=eval_in.periodo.strip(),
        data_avaliacao=eval_in.data_avaliacao,
        conceito=eval_in.conceito.value,
        nota=eval_in.nota,
        relatorio_descritivo=eval_in.relatorio_descritivo.strip()
    )
    db.add(nova_avaliacao)
    db.commit()
    db.refresh(nova_avaliacao)

    resp = EvaluationResponse.model_validate(nova_avaliacao)
    resp.aluno_nome = aluno.nome
    resp.turma_nome = turma.nome
    resp.professor_nome = prof.nome
    return resp


@router.get(
    "/evaluations/student/{aluno_id}",
    response_model=List[EvaluationResponse],
    summary="Obter portfólio e avaliações descritivas do aluno"
)
def get_student_evaluations(
    aluno_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    avaliacoes = db.query(Evaluation).options(
        joinedload(Evaluation.aluno),
        joinedload(Evaluation.turma),
        joinedload(Evaluation.professor)
    ).filter(Evaluation.aluno_id == aluno_id).order_by(Evaluation.data_avaliacao.desc()).all()

    res = []
    for ev in avaliacoes:
        r = EvaluationResponse.model_validate(ev)
        if ev.aluno:
            r.aluno_nome = ev.aluno.nome
        if ev.turma:
            r.turma_nome = ev.turma.nome
        if ev.professor:
            r.professor_nome = ev.professor.nome
        res.append(r)
    return res


# ─── Relatórios de Frequência e Presença ──────────────────────────────────────

@router.get(
    "/reports/classes-summary",
    response_model=List[ClassAttendanceSummary],
    summary="Relatório geral de presenças e frequência por turma"
)
def get_classes_attendance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    turmas = db.query(ClassGroup).options(
        joinedload(ClassGroup.curso),
        joinedload(ClassGroup.professor)
    ).filter(ClassGroup.ativa.is_(True)).order_by(ClassGroup.nome.asc()).all()

    # Se for professor, limitar às turmas dele
    if current_user.role == UserRole.PROFESSOR.value:
        prof = db.query(Teacher).filter((Teacher.user_id == current_user.id) | (Teacher.email == current_user.email)).first()
        if prof:
            turmas = [t for t in turmas if t.professor_id == prof.id]

    res = []
    for turma in turmas:
        lessons = db.query(Lesson).filter(Lesson.turma_id == turma.id).all()
        lesson_ids = [l.id for l in lessons]

        presencas = 0
        faltas = 0
        justificadas = 0

        if lesson_ids:
            attendances = db.query(Attendance).filter(Attendance.lesson_id.in_(lesson_ids)).all()
            for att in attendances:
                if att.status == StatusPresenca.PRESENTE.value:
                    presencas += 1
                elif att.status == StatusPresenca.FALTA.value:
                    faltas += 1
                elif att.status == StatusPresenca.JUSTIFICADA.value:
                    justificadas += 1

        total_regs = presencas + faltas + justificadas
        taxa = round((presencas / total_regs) * 100, 1) if total_regs > 0 else 100.0

        matriculados = db.query(Matricula).filter(
            Matricula.turma_id == turma.id,
            Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value])
        ).count()

        res.append(ClassAttendanceSummary(
            turma_id=turma.id,
            turma_nome=turma.nome,
            curso_nome=turma.curso.nome if turma.curso else "Sem curso",
            professor_nome=turma.professor.nome if turma.professor else "Sem professor",
            dia_semana=turma.dia_semana,
            horario=f"{turma.horario_inicio}-{turma.horario_fim}",
            total_matriculados=matriculados,
            capacidade_maxima=turma.capacidade_maxima,
            total_aulas=len(lessons),
            total_aulas_registradas=len(lessons),
            total_registros=total_regs,
            total_presencas=presencas,
            total_faltas=faltas,
            total_justificadas=justificadas,
            taxa_presenca_percentual=taxa
        ))
    return res


@router.get(
    "/reports/student-history",
    response_model=StudentAttendanceReport,
    summary="Histórico e taxa de frequência detalhada do aluno"
)
def get_student_attendance_history(
    aluno_id: int = Query(..., description="ID do aluno"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    attendances = db.query(Attendance).options(
        joinedload(Attendance.lesson).joinedload(Lesson.turma)
    ).filter(Attendance.aluno_id == aluno_id).all()

    presencas = 0
    faltas = 0
    justificadas = 0
    registros = []

    for att in attendances:
        if att.status == StatusPresenca.PRESENTE.value:
            presencas += 1
        elif att.status == StatusPresenca.FALTA.value:
            faltas += 1
        elif att.status == StatusPresenca.JUSTIFICADA.value:
            justificadas += 1

        data_aula = att.lesson.data_aula if att.lesson else date.today()
        turma_id = att.lesson.turma_id if att.lesson else 0
        turma_nome = att.lesson.turma.nome if att.lesson and att.lesson.turma else "Turma"
        tema = att.lesson.tema_aula if att.lesson else "Aula"

        registros.append(AttendanceRecordItem(
            data_aula=data_aula,
            turma_id=turma_id,
            turma_nome=turma_nome,
            tema_aula=tema,
            status=att.status,
            motivo_justificativa=att.motivo_justificativa,
            observacao=att.motivo_justificativa
        ))

    # Ordenar registros por data decrescente
    registros.sort(key=lambda r: r.data_aula, reverse=True)
    total_regs = presencas + faltas + justificadas
    taxa = round((presencas / total_regs) * 100, 1) if total_regs > 0 else 100.0

    return StudentAttendanceReport(
        aluno_id=aluno.id,
        aluno_nome=aluno.nome,
        total_aulas=len(attendances),
        total_registros=total_regs,
        total_presencas=presencas,
        total_faltas=faltas,
        total_justificadas=justificadas,
        total_faltas_justificadas=justificadas,
        taxa_presenca_percentual=taxa,
        registros=registros,
        historico=registros
    )
