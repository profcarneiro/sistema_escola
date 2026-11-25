from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.room import Room
from app.models.class_group import ClassGroup
from app.models.user import User, UserRole
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse
from app.routers.auth import get_current_active_user, require_roles

router = APIRouter(prefix="/rooms", tags=["Salas e Estúdios"])


@router.get("/", response_model=List[RoomResponse], summary="Listar salas de aula")
def list_rooms(
    apenas_ativas: bool = Query(True, description="Filtrar apenas salas ativas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retorna todas as salas cadastradas na escola."""
    query = db.query(Room)
    if apenas_ativas:
        query = query.filter(Room.ativa.is_(True))
    return query.order_by(Room.nome.asc()).all()


@router.post(
    "/",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar nova sala (Direção ou Coordenação)"
)
def create_room(
    room_in: RoomCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    """Cadastra uma sala física com capacidade configurável."""
    nome_clean = room_in.nome.strip()
    existing = db.query(Room).filter(Room.nome.ilike(nome_clean)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe uma sala cadastrada com o nome '{nome_clean}'."
        )

    nova_sala = Room(
        nome=nome_clean,
        capacidade=room_in.capacidade,
        descricao=room_in.descricao.strip() if room_in.descricao else None,
        ativa=True
    )
    db.add(nova_sala)
    db.commit()
    db.refresh(nova_sala)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="SALA_CRIADA",
        entidade="Room",
        registro_id=str(nova_sala.id),
        detalhes={"nome": nova_sala.nome, "capacidade": nova_sala.capacidade},
        usuario=current_user,
        ip=client_ip
    )
    return nova_sala


@router.get("/{room_id}", response_model=RoomResponse, summary="Obter dados de uma sala por ID")
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    return room


@router.put("/{room_id}", response_model=RoomResponse, summary="Atualizar dados de uma sala")
def update_room(
    room_id: int,
    room_update: RoomUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")

    if room_update.nome is not None:
        nome_clean = room_update.nome.strip()
        if nome_clean.lower() != room.nome.lower():
            existing = db.query(Room).filter(Room.nome.ilike(nome_clean)).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe uma sala com o nome '{nome_clean}'."
                )
            room.nome = nome_clean

    if room_update.capacidade is not None:
        room.capacidade = room_update.capacidade
    if room_update.descricao is not None:
        room.descricao = room_update.descricao.strip() if room_update.descricao else None
    if room_update.ativa is not None:
        room.ativa = room_update.ativa

    db.commit()
    db.refresh(room)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="SALA_ATUALIZADA",
        entidade="Room",
        registro_id=str(room.id),
        detalhes={"nome": room.nome, "capacidade": room.capacidade, "ativa": room.ativa},
        usuario=current_user,
        ip=client_ip
    )
    return room


@router.delete("/{room_id}", status_code=status.HTTP_200_OK, summary="Excluir ou desativar sala")
def delete_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")

    has_classes = db.query(ClassGroup).filter(ClassGroup.sala_id == room_id).count()
    if has_classes > 0:
        room.ativa = False
        db.commit()
        db.refresh(room)
        msg = f"Sala '{room.nome}' possui turmas vinculadas e foi desativada com sucesso."
    else:
        db.delete(room)
        db.commit()
        msg = f"Sala '{room.nome}' excluída com sucesso."

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="SALA_EXCLUIDA",
        entidade="Room",
        registro_id=str(room_id),
        detalhes={"acao": msg},
        usuario=current_user,
        ip=client_ip
    )
    return {"status": "ok", "mensagem": msg}
