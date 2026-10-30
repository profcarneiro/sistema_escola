from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/courses", tags=["Cursos e Modalidades"])


@router.get("/", response_model=List[CourseResponse], summary="Listar cursos e modalidades artísticas")
def list_courses(
    apenas_ativos: bool = Query(True, description="Filtrar apenas modalidades ativas"),
    busca: Optional[str] = Query(None, description="Busca por nome da modalidade"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Course)
    if apenas_ativos:
        query = query.filter(Course.ativo.is_(True))
    if busca:
        query = query.filter(Course.nome.ilike(f"%{busca.strip()}%"))
    return query.order_by(Course.nome.asc()).all()


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar nova modalidade artística (Direção ou Coordenação)"
)
def create_course(
    course_in: CourseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    nome_clean = course_in.nome.strip()
    existing = db.query(Course).filter(Course.nome.ilike(nome_clean)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe uma modalidade com o nome '{nome_clean}'."
        )

    novo_curso = Course(
        nome=nome_clean,
        descricao=course_in.descricao.strip() if course_in.descricao else None,
        duracao_meses=course_in.duracao_meses,
        valor_mensalidade=course_in.valor_mensalidade,
        ativo=True
    )
    db.add(novo_curso)
    db.commit()
    db.refresh(novo_curso)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="CURSO_CRIADO",
        entidade="Course",
        registro_id=str(novo_curso.id),
        detalhes={"nome": novo_curso.nome, "mensalidade": novo_curso.valor_mensalidade},
        usuario=current_user,
        ip=client_ip
    )
    return novo_curso


@router.get("/{course_id}", response_model=CourseResponse, summary="Obter dados de uma modalidade por ID")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalidade artística não encontrada.")
    return course


@router.put("/{course_id}", response_model=CourseResponse, summary="Atualizar modalidade artística")
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modalidade não encontrada.")

    if course_update.nome is not None:
        nome_clean = course_update.nome.strip()
        if nome_clean.lower() != course.nome.lower():
            existing = db.query(Course).filter(Course.nome.ilike(nome_clean)).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe uma modalidade com o nome '{nome_clean}'."
                )
            course.nome = nome_clean

    if course_update.descricao is not None:
        course.descricao = course_update.descricao.strip() if course_update.descricao else None
    if course_update.duracao_meses is not None:
        course.duracao_meses = course_update.duracao_meses
    if course_update.valor_mensalidade is not None:
        course.valor_mensalidade = course_update.valor_mensalidade
    if course_update.ativo is not None:
        course.ativo = course_update.ativo

    db.commit()
    db.refresh(course)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="CURSO_ATUALIZADO",
        entidade="Course",
        registro_id=str(course.id),
        detalhes={"nome": course.nome, "ativo": course.ativo},
        usuario=current_user,
        ip=client_ip
    )
    return course
