from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.student import Aluno
from app.models.guardian import Responsavel
from app.models.user import User, UserRole
from app.schemas.student import AlunoCreate, AlunoUpdate, AlunoResponse
from app.schemas.guardian import ResponsavelCreate, ResponsavelUpdate, ResponsavelResponse
from app.routers.auth import get_current_active_user, require_roles


def calcular_idade(data_nascimento: date) -> int:
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )


router = APIRouter(prefix="/students", tags=["Alunos e Responsáveis"])


@router.get("/", response_model=List[AlunoResponse], summary="Listar alunos")
def list_students(
    apenas_ativos: bool = Query(True, description="Filtrar apenas alunos ativos"),
    busca: Optional[str] = Query(None, description="Busca por nome do aluno"),
    menor_de_idade: Optional[bool] = Query(None, description="Filtrar apenas menores/maiores"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista alunos cadastrados. Dados completos incluindo responsável."""
    query = db.query(Aluno).options(joinedload(Aluno.responsavel))
    if apenas_ativos:
        query = query.filter(Aluno.ativo.is_(True))
    if busca:
        query = query.filter(Aluno.nome.ilike(f"%{busca.strip()}%"))

    alunos = query.order_by(Aluno.nome.asc()).all()

    if menor_de_idade is not None:
        hoje = date.today()
        alunos = [
            a for a in alunos
            if (calcular_idade(a.data_nascimento) < 18) == menor_de_idade
        ]
    return alunos


@router.post(
    "/",
    response_model=AlunoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo aluno"
)
def create_student(
    aluno_in: AlunoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    """
    Cadastra um aluno. Para menores de 18 anos, o responsável é OBRIGATÓRIO.
    Um aluno só pode ter UM responsável (regra explícita da escola).
    """
    client_ip = request.client.host if request.client else None
    idade = calcular_idade(aluno_in.data_nascimento)

    # Validação extra de menor sem responsável (dupla segurança além do schema)
    if idade < 18 and aluno_in.responsavel is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Alunos menores de 18 anos exigem cadastro de responsável legal e financeiro."
        )

    novo_aluno = Aluno(
        nome=aluno_in.nome.strip(),
        data_nascimento=aluno_in.data_nascimento,
        cpf=aluno_in.cpf.strip() if aluno_in.cpf else None,
        email=aluno_in.email.strip().lower() if aluno_in.email else None,
        telefone=aluno_in.telefone.strip() if aluno_in.telefone else None,
        endereco=aluno_in.endereco.strip() if aluno_in.endereco else None,
        alergias=aluno_in.alergias,
        medicacoes=aluno_in.medicacoes,
        observacoes_saude=aluno_in.observacoes_saude,
        autorizacao_imagem=aluno_in.autorizacao_imagem,
        autorizacao_imagem_data=datetime.now(timezone.utc) if aluno_in.autorizacao_imagem else None,
        ativo=True
    )
    db.add(novo_aluno)
    db.flush()  # gera o ID do aluno antes de criar o responsável

    # Cadastro do responsável (se informado)
    if aluno_in.responsavel:
        responsavel = Responsavel(
            aluno_id=novo_aluno.id,
            nome=aluno_in.responsavel.nome.strip(),
            cpf=aluno_in.responsavel.cpf.strip(),
            telefone=aluno_in.responsavel.telefone.strip(),
            email=aluno_in.responsavel.email.strip().lower(),
            endereco=aluno_in.responsavel.endereco.strip(),
            responsavel_financeiro=True,
            ativo=True
        )
        db.add(responsavel)

    db.commit()
    db.refresh(novo_aluno)

    registrar_auditoria(
        db=db,
        acao="ALUNO_CADASTRADO",
        entidade="Aluno",
        registro_id=str(novo_aluno.id),
        detalhes={
            "nome": novo_aluno.nome,
            "nascimento": str(novo_aluno.data_nascimento),
            "idade": idade,
            "menor_de_idade": idade < 18,
            "tem_responsavel": aluno_in.responsavel is not None
        },
        usuario=current_user,
        ip=client_ip
    )
    return novo_aluno


@router.get("/{aluno_id}", response_model=AlunoResponse, summary="Obter dados do aluno por ID")
def get_student(
    aluno_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")
    return aluno


@router.put("/{aluno_id}", response_model=AlunoResponse, summary="Atualizar dados do aluno")
def update_student(
    aluno_id: int,
    aluno_update: AlunoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    aluno = db.query(Aluno).options(joinedload(Aluno.responsavel)).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    if aluno_update.nome is not None:
        aluno.nome = aluno_update.nome.strip()
    if aluno_update.data_nascimento is not None:
        aluno.data_nascimento = aluno_update.data_nascimento
    if aluno_update.cpf is not None:
        aluno.cpf = aluno_update.cpf.strip() if aluno_update.cpf else None
    if aluno_update.email is not None:
        aluno.email = aluno_update.email.strip().lower()
    if aluno_update.telefone is not None:
        aluno.telefone = aluno_update.telefone.strip()
    if aluno_update.endereco is not None:
        aluno.endereco = aluno_update.endereco.strip()
    if aluno_update.alergias is not None:
        aluno.alergias = aluno_update.alergias
    if aluno_update.medicacoes is not None:
        aluno.medicacoes = aluno_update.medicacoes
    if aluno_update.observacoes_saude is not None:
        aluno.observacoes_saude = aluno_update.observacoes_saude
    if aluno_update.autorizacao_imagem is not None:
        aluno.autorizacao_imagem = aluno_update.autorizacao_imagem
        if aluno_update.autorizacao_imagem:
            aluno.autorizacao_imagem_data = datetime.now(timezone.utc)
    if aluno_update.ativo is not None:
        aluno.ativo = aluno_update.ativo

    db.commit()
    db.refresh(aluno)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="ALUNO_ATUALIZADO",
        entidade="Aluno",
        registro_id=str(aluno.id),
        detalhes={"nome": aluno.nome, "ativo": aluno.ativo},
        usuario=current_user,
        ip=client_ip
    )
    return aluno


# ─── Endpoints de Responsável ──────────────────────────────────────────────────

@router.get("/{aluno_id}/responsavel", response_model=ResponsavelResponse, summary="Obter responsável do aluno")
def get_guardian(
    aluno_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    responsavel = db.query(Responsavel).filter(Responsavel.aluno_id == aluno_id).first()
    if not responsavel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsável não encontrado para este aluno.")
    return responsavel


@router.post(
    "/{aluno_id}/responsavel",
    response_model=ResponsavelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular responsável ao aluno"
)
def create_guardian(
    aluno_id: int,
    resp_in: ResponsavelCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    """
    Cadastra o responsável de um aluno.
    REGRA: Um aluno pode ter SOMENTE um responsável. Tentativa de adicionar segundo
    responsável será bloqueada pela constraint do banco e pela verificação prévia.
    """
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    # Verifica se já existe responsável (REGRA CRÍTICA: apenas 1 por aluno)
    existente = db.query(Responsavel).filter(Responsavel.aluno_id == aluno_id).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este aluno já possui um responsável cadastrado. Um aluno não pode ter mais de um responsável."
        )

    novo_responsavel = Responsavel(
        aluno_id=aluno_id,
        nome=resp_in.nome.strip(),
        cpf=resp_in.cpf.strip(),
        telefone=resp_in.telefone.strip(),
        email=resp_in.email.strip().lower(),
        endereco=resp_in.endereco.strip(),
        responsavel_financeiro=True,
        ativo=True
    )
    db.add(novo_responsavel)
    db.commit()
    db.refresh(novo_responsavel)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="RESPONSAVEL_CADASTRADO",
        entidade="Responsavel",
        registro_id=str(novo_responsavel.id),
        detalhes={"aluno_id": aluno_id, "responsavel_nome": novo_responsavel.nome},
        usuario=current_user,
        ip=client_ip
    )
    return novo_responsavel


@router.put("/{aluno_id}/responsavel", response_model=ResponsavelResponse, summary="Atualizar responsável")
def update_guardian(
    aluno_id: int,
    resp_update: ResponsavelUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.DIRECAO.value, UserRole.COORDENACAO.value, UserRole.SECRETARIA.value
    ))
):
    responsavel = db.query(Responsavel).filter(Responsavel.aluno_id == aluno_id).first()
    if not responsavel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsável não encontrado.")

    if resp_update.nome is not None:
        responsavel.nome = resp_update.nome.strip()
    if resp_update.cpf is not None:
        responsavel.cpf = resp_update.cpf.strip()
    if resp_update.telefone is not None:
        responsavel.telefone = resp_update.telefone.strip()
    if resp_update.email is not None:
        responsavel.email = resp_update.email.strip().lower()
    if resp_update.endereco is not None:
        responsavel.endereco = resp_update.endereco.strip()

    db.commit()
    db.refresh(responsavel)
    return responsavel
