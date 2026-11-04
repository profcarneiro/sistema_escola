from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup
from app.models.user import User, UserRole
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/teachers", tags=["Professores"])


@router.get("/", response_model=List[TeacherResponse], summary="Listar professores")
def list_teachers(
    apenas_ativos: bool = Query(True, description="Filtrar apenas professores ativos"),
    especialidade: Optional[str] = Query(None, description="Filtrar por especialidade"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Teacher)
    if apenas_ativos:
        query = query.filter(Teacher.ativo.is_(True))
    if especialidade:
        query = query.filter(Teacher.especialidades.ilike(f"%{especialidade.strip()}%"))
    return query.order_by(Teacher.nome.asc()).all()


@router.post(
    "/",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo professor"
)
def create_teacher(
    teacher_in: TeacherCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    email_clean = teacher_in.email.strip().lower()
    existing = db.query(Teacher).filter(Teacher.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um professor cadastrado com este e-mail."
        )

    # Valida substituto se informado
    if teacher_in.substituto_id is not None:
        substituto = db.query(Teacher).filter(Teacher.id == teacher_in.substituto_id).first()
        if not substituto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professor substituto indicado não foi encontrado."
            )

    # Valida user_id se informado
    if teacher_in.user_id is not None:
        user = db.query(User).filter(User.id == teacher_in.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário do sistema vinculado não encontrado."
            )

    novo_professor = Teacher(
        nome=teacher_in.nome.strip(),
        email=email_clean,
        telefone=teacher_in.telefone.strip() if teacher_in.telefone else None,
        endereco=teacher_in.endereco.strip() if teacher_in.endereco else None,
        especialidades=teacher_in.especialidades.strip() if teacher_in.especialidades else None,
        disponibilidade=teacher_in.disponibilidade.strip() if teacher_in.disponibilidade else None,
        substituto_id=teacher_in.substituto_id,
        user_id=teacher_in.user_id,
        ativo=True
    )
    db.add(novo_professor)
    db.commit()
    db.refresh(novo_professor)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="PROFESSOR_CRIADO",
        entidade="Teacher",
        registro_id=str(novo_professor.id),
        detalhes={"nome": novo_professor.nome, "email": novo_professor.email},
        usuario=current_user,
        ip=client_ip
    )
    return novo_professor


@router.get("/{teacher_id}", response_model=TeacherResponse, summary="Obter dados de um professor por ID")
def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")
    return teacher


@router.put("/{teacher_id}", response_model=TeacherResponse, summary="Atualizar dados do professor")
def update_teacher(
    teacher_id: int,
    teacher_update: TeacherUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value))
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")

    if teacher_update.substituto_id is not None:
        if teacher_update.substituto_id == teacher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Um professor não pode ser substituto de si mesmo."
            )
        substituto = db.query(Teacher).filter(Teacher.id == teacher_update.substituto_id).first()
        if not substituto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professor substituto indicado não encontrado."
            )
        teacher.substituto_id = teacher_update.substituto_id

    if teacher_update.email is not None:
        email_clean = teacher_update.email.strip().lower()
        if email_clean != teacher.email:
            existing = db.query(Teacher).filter(Teacher.email == email_clean).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já está sendo utilizado por outro professor."
                )
            teacher.email = email_clean

    if teacher_update.nome is not None:
        teacher.nome = teacher_update.nome.strip()
    if teacher_update.telefone is not None:
        teacher.telefone = teacher_update.telefone.strip() if teacher_update.telefone else None
    if teacher_update.endereco is not None:
        teacher.endereco = teacher_update.endereco.strip() if teacher_update.endereco else None
    if teacher_update.especialidades is not None:
        teacher.especialidades = teacher_update.especialidades.strip() if teacher_update.especialidades else None
    if teacher_update.disponibilidade is not None:
        teacher.disponibilidade = teacher_update.disponibilidade.strip() if teacher_update.disponibilidade else None
    if teacher_update.user_id is not None:
        teacher.user_id = teacher_update.user_id
    if teacher_update.ativo is not None:
        teacher.ativo = teacher_update.ativo

    db.commit()
    db.refresh(teacher)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="PROFESSOR_ATUALIZADO",
        entidade="Teacher",
        registro_id=str(teacher.id),
        detalhes={"nome": teacher.nome, "email": teacher.email, "ativo": teacher.ativo},
        usuario=current_user,
        ip=client_ip
    )
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_200_OK, summary="Excluir ou desativar professor")
def delete_teacher(
    teacher_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado.")

    has_classes = db.query(ClassGroup).filter(ClassGroup.professor_id == teacher_id).count()
    if has_classes > 0:
        teacher.ativo = False
        db.commit()
        db.refresh(teacher)
        msg = f"Professor(a) '{teacher.nome}' possui turmas vinculadas e foi desativado(a)."
    else:
        db.delete(teacher)
        db.commit()
        msg = f"Professor(a) '{teacher.nome}' excluído(a) com sucesso."

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="PROFESSOR_EXCLUIDO",
        entidade="Teacher",
        registro_id=str(teacher_id),
        detalhes={"acao": msg},
        usuario=current_user,
        ip=client_ip
    )
    return {"status": "ok", "mensagem": msg}
