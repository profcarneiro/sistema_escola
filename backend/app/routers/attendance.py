import calendar
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
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
from app.models.operations import TeacherClosing, AttendanceChangeLog, StatusFechamento
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.attendance import (
    LessonCreate, LessonUpdate, LessonResponse,
    AttendanceBatchCreate, AttendanceResponse,
    ClassMakeUpCreate, ClassMakeUpResponse,
    EvaluationCreate, EvaluationResponse,
    validar_janela_reposicao,
    ClassAttendanceSummary, StudentAttendanceReport, AttendanceRecordItem,
    MissingCallAlertItem, MonthlyStudentAttendanceItem,
)
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/attendance", tags=["Frequência, Diário e Reposições"])


def _check_teacher_month_lock(db: Session, professor_id: int, data_aula: date) -> Optional[TeacherClosing]:
    competencia = data_aula.strftime("%Y-%m")
    return db.query(TeacherClosing).filter(
        TeacherClosing.professor_id == professor_id,
        TeacherClosing.competencia == competencia,
        TeacherClosing.status.in_([
            StatusFechamento.FECHADO.value,
            StatusFechamento.PAGO_PARCIAL.value,
            StatusFechamento.PAGO.value,
        ]),
    ).first()


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
        observacoes=lesson_in.observacoes,
        cancelada_professor=bool(lesson_in.cancelada_professor),
    )
    db.add(nova_aula)
    db.commit()
    db.refresh(nova_aula)

    resp = LessonResponse.model_validate(nova_aula)
    resp.turma_nome = turma.nome
    resp.professor_nome = prof.nome
    return resp


@router.put("/lessons/{lesson_id}", response_model=LessonResponse, summary="Atualizar aula / sinalizar cancelamento pelo professor")
def update_lesson(
    lesson_id: int,
    lesson_in: LessonUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value
    ))
):
    lesson = db.query(Lesson).options(joinedload(Lesson.turma), joinedload(Lesson.professor)).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")

    lock = _check_teacher_month_lock(db, lesson.professor_id, lesson.data_aula)
    if lock:
        if current_user.role != UserRole.DIRECAO.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Alteração bloqueada: o fechamento mensal do professor já foi encerrado/pago. Somente a Direção pode alterar."
            )
        if not (lesson_in.motivo_alteracao and lesson_in.motivo_alteracao.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competência fechada: informe o motivo da alteração para registrar no histórico."
            )

    if lesson_in.tema_aula is not None:
        lesson.tema_aula = lesson_in.tema_aula.strip()
    if lesson_in.conteudo_programatico is not None:
        lesson.conteudo_programatico = lesson_in.conteudo_programatico
    if lesson_in.materiais_utilizados is not None:
        lesson.materiais_utilizados = lesson_in.materiais_utilizados
    if lesson_in.observacoes is not None:
        lesson.observacoes = lesson_in.observacoes
    if lesson_in.cancelada_professor is not None:
        lesson.cancelada_professor = bool(lesson_in.cancelada_professor)

    db.commit()
    db.refresh(lesson)

    if lock and lesson_in.motivo_alteracao:
        registrar_auditoria(
            db=db,
            acao="AULA_ALTERADA_APOS_FECHAMENTO",
            entidade="Lesson",
            registro_id=str(lesson.id),
            detalhes={"motivo": lesson_in.motivo_alteracao.strip(), "cancelada_professor": lesson.cancelada_professor},
            usuario=current_user,
            ip=request.client.host if request.client else None,
        )

    resp = LessonResponse.model_validate(lesson)
    resp.turma_nome = lesson.turma.nome if lesson.turma else None
    resp.professor_nome = lesson.professor.nome if lesson.professor else None
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

    lock = _check_teacher_month_lock(db, lesson.professor_id, lesson.data_aula)
    if lock:
        if current_user.role != UserRole.DIRECAO.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chamada bloqueada: o pagamento deste professor nesta competência já foi fechado/pago."
            )
        if not (batch_in.motivo_alteracao and batch_in.motivo_alteracao.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competência fechada: informe o motivo_alteracao para registrar no histórico de alterações."
            )

    registros = []
    alteracoes_pendentes = []
    for item in batch_in.frequencias:
        # Se já existe para este aluno nesta aula, atualiza
        existente = db.query(Attendance).filter(
            Attendance.lesson_id == lesson_id,
            Attendance.aluno_id == item.aluno_id
        ).first()

        if existente:
            status_ant = existente.status
            repo_ant = bool(existente.eh_reposicao)
            mudou = (status_ant != item.status.value) or (repo_ant != bool(item.eh_reposicao))
            existente.status = item.status.value
            existente.motivo_justificativa = item.motivo_justificativa
            existente.eh_reposicao = bool(item.eh_reposicao)
            if item.makeup_id is not None:
                existente.makeup_id = item.makeup_id
            registros.append(existente)
            if mudou or lock:
                alteracoes_pendentes.append((existente, status_ant, item.status.value))
        else:
            novo = Attendance(
                lesson_id=lesson_id,
                aluno_id=item.aluno_id,
                matricula_id=item.matricula_id,
                status=item.status.value,
                motivo_justificativa=item.motivo_justificativa,
                eh_reposicao=bool(item.eh_reposicao),
                makeup_id=item.makeup_id,
            )
            db.add(novo)
            registros.append(novo)
            if lock:
                alteracoes_pendentes.append((novo, None, item.status.value))

        if item.makeup_id and item.status == StatusPresenca.PRESENTE:
            makeup = db.query(ClassMakeUp).filter(ClassMakeUp.id == item.makeup_id).first()
            if makeup and makeup.status == StatusReposicao.AGENDADA.value:
                makeup.status = StatusReposicao.REALIZADA.value

    db.flush()
    for att_obj, st_ant, st_nov in alteracoes_pendentes:
        motivo_txt = (
            batch_in.motivo_alteracao.strip()
            if (batch_in.motivo_alteracao and batch_in.motivo_alteracao.strip())
            else "Atualização de chamada"
        )
        db.add(AttendanceChangeLog(
            attendance_id=att_obj.id,
            lesson_id=lesson_id,
            aluno_id=att_obj.aluno_id,
            alterado_por_id=current_user.id,
            alterado_por_nome=current_user.nome,
            status_anterior=st_ant,
            status_novo=st_nov,
            competencia=lesson.data_aula.strftime("%Y-%m"),
            motivo=motivo_txt,
        ))

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

    # 4. Verifica capacidade máxima da turma de destino
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
                f"{turma_destino.capacidade_maxima} alunos para esta data."
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
        joinedload(ClassGroup.cursos),
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

        cursos_nomes = [c.nome for c in (turma.cursos or [])]
        if not cursos_nomes and turma.curso:
            cursos_nomes = [turma.curso.nome]

        res.append(ClassAttendanceSummary(
            turma_id=turma.id,
            turma_nome=turma.nome,
            curso_nome=", ".join(cursos_nomes) if cursos_nomes else "Sem curso",
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


def _weekday_indices_from_text(dia_texto: Optional[str]) -> List[int]:
    if not dia_texto:
        return []
    norm = unicodedata.normalize("NFKD", dia_texto).encode("ascii", "ignore").decode("ascii").upper()
    mapping = [
        ("SEGUNDA", 0),
        ("TERCA", 1),
        ("QUARTA", 2),
        ("QUINTA", 3),
        ("SEXTA", 4),
        ("SABADO", 5),
        ("DOMINGO", 6),
    ]
    return [idx for token, idx in mapping if token in norm]


@router.get(
    "/alerts/missing-calls",
    response_model=List[MissingCallAlertItem],
    summary="Alertas de aulas ocorridas sem chamada lançada"
)
def get_missing_calls_alerts(
    competencia: Optional[str] = Query(None, description="Competência YYYY-MM (padrão mês atual)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value, UserRole.SECRETARIA.value
    )),
):
    hoje = date.today()
    if competencia:
        ano, mes = map(int, competencia.split("-"))
    else:
        ano, mes = hoje.year, hoje.month

    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    limite_data = min(hoje, fim_mes)
    if limite_data < inicio_mes:
        return []

    turmas = db.query(ClassGroup).options(joinedload(ClassGroup.professor)).filter(ClassGroup.ativa.is_(True)).all()
    alertas: List[MissingCallAlertItem] = []

    for t in turmas:
        matriculas_ativas = db.query(Matricula).filter(
            Matricula.turma_id == t.id,
            Matricula.status.in_([StatusMatricula.ATIVA.value, StatusMatricula.EXPERIMENTAL.value]),
        ).all()
        if not matriculas_ativas:
            continue

        min_inicio = min(m.data_inicio for m in matriculas_ativas if m.data_inicio) if any(m.data_inicio for m in matriculas_ativas) else inicio_mes
        aulas_mes = db.query(Lesson).options(joinedload(Lesson.frequencias)).filter(
            Lesson.turma_id == t.id,
            Lesson.data_aula >= inicio_mes,
            Lesson.data_aula <= limite_data,
        ).all()
        aulas_por_data = {a.data_aula: a for a in aulas_mes}

        # 1) Aulas registradas no diário sem nenhum registro de presença (exceto canceladas pelo professor)
        for aula in aulas_mes:
            if not aula.cancelada_professor and len(aula.frequencias or []) == 0:
                alertas.append(MissingCallAlertItem(
                    turma_id=t.id,
                    turma_nome=t.nome,
                    professor_nome=t.professor.nome if t.professor else None,
                    dia_semana=t.dia_semana,
                    horario=f"{t.horario_inicio}-{t.horario_fim}",
                    data_referencia=aula.data_aula,
                    motivo="Aula registrada no diário sem chamada lançada",
                    lesson_id=aula.id,
                ))

        # 2) Datas previstas na grade da turma até limite_data sem aula lançada no diário
        dias_semana_turma = _weekday_indices_from_text(t.dia_semana)
        if dias_semana_turma:
            cursor = max(inicio_mes, min_inicio)
            while cursor <= limite_data:
                if cursor.weekday() in dias_semana_turma and cursor not in aulas_por_data:
                    alertas.append(MissingCallAlertItem(
                        turma_id=t.id,
                        turma_nome=t.nome,
                        professor_nome=t.professor.nome if t.professor else None,
                        dia_semana=t.dia_semana,
                        horario=f"{t.horario_inicio}-{t.horario_fim}",
                        data_referencia=cursor,
                        motivo="Aula ocorrida pela grade sem diário/chamada lançada",
                        lesson_id=None,
                    ))
                cursor += timedelta(days=1)

    alertas.sort(key=lambda a: (a.data_referencia, a.turma_nome), reverse=True)
    return alertas


@router.get(
    "/reports/monthly-students",
    response_model=List[MonthlyStudentAttendanceItem],
    summary="Relatório mensal de frequência por aluno (presenças x faltas)"
)
def get_monthly_students_report(
    competencia: str = Query(..., description="Competência YYYY-MM"),
    turma_id: Optional[int] = Query(None, description="Filtrar por turma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.PROFESSOR.value, UserRole.FINANCEIRO.value, UserRole.SECRETARIA.value
    )),
):
    ano, mes = map(int, competencia.split("-"))
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])

    query = db.query(Attendance).options(
        joinedload(Attendance.aluno),
        joinedload(Attendance.lesson).joinedload(Lesson.turma),
    ).join(Lesson, Attendance.lesson_id == Lesson.id).filter(
        Lesson.data_aula >= inicio_mes,
        Lesson.data_aula <= fim_mes,
        Lesson.cancelada_professor.is_(False),
    )
    if turma_id is not None:
        query = query.filter(Lesson.turma_id == turma_id)

    registros = query.all()
    agregado: Dict[tuple, Dict] = {}

    for att in registros:
        turma_obj = att.lesson.turma if att.lesson else None
        tid = att.lesson.turma_id if att.lesson else 0
        key = (att.aluno_id, tid)
        slot = agregado.setdefault(key, {
            "aluno_id": att.aluno_id,
            "aluno_nome": att.aluno.nome if att.aluno else f"Aluno #{att.aluno_id}",
            "turma_id": tid,
            "turma_nome": turma_obj.nome if turma_obj else f"Turma #{tid}",
            "presencas": 0,
            "faltas": 0,
            "justificadas": 0,
            "reposicoes": 0,
        })
        if att.status == StatusPresenca.PRESENTE.value:
            slot["presencas"] += 1
            if getattr(att, "eh_reposicao", False):
                slot["reposicoes"] += 1
        elif att.status == StatusPresenca.FALTA.value:
            slot["faltas"] += 1
        elif att.status == StatusPresenca.JUSTIFICADA.value:
            slot["justificadas"] += 1

    resultado: List[MonthlyStudentAttendanceItem] = []
    for item in agregado.values():
        total = item["presencas"] + item["faltas"] + item["justificadas"]
        taxa = round((item["presencas"] / total) * 100, 1) if total > 0 else 100.0
        resultado.append(MonthlyStudentAttendanceItem(
            **item,
            taxa_presenca_percentual=taxa,
        ))

    resultado.sort(key=lambda x: (x.aluno_nome, x.turma_nome))
    return resultado
