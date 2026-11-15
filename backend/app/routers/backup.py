import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.audit import registrar_auditoria
from app.database import get_db
from app.models.user import User, UserRole
from app.routers.auth import require_roles
from app.services.remote_backup import (
    BACKUP_DIR,
    RemoteBackupError,
    SupabaseStorageClient,
    carregar_config_remota,
    get_supabase_client_from_config,
    mask_secret,
    salvar_config_remota,
)

router = APIRouter(prefix="/backup", tags=["Segurança e Backup"])


class BackupItem(BaseModel):
    arquivo: str
    tamanho_bytes: int
    tamanho_formatado: str
    criado_em: str
    enviado_remoto: bool = False
    remoto_mensagem: Optional[str] = None


class RemoteBackupItem(BaseModel):
    arquivo: str
    caminho_remoto: str
    tamanho_bytes: int
    tamanho_formatado: str
    criado_em: str


class RemoteConfigStatus(BaseModel):
    configurado: bool
    provedor: str = "supabase"
    supabase_url: str = ""
    bucket: str = "backups"
    prefixo: str = "escola-artes"
    auto_enviar_ao_criar: bool = False
    chave_mascarada: Optional[str] = None
    origem: str = "nao_configurado"


class RemoteConfigUpdate(BaseModel):
    supabase_url: str = Field(..., min_length=8, description="URL do projeto Supabase (ex: https://xxx.supabase.co)")
    service_role_key: Optional[str] = Field(None, description="Service Role Key do Supabase (opcional ao atualizar apenas bucket/prefixo)")
    bucket: str = Field("backups", min_length=1, max_length=100)
    prefixo: str = Field("escola-artes", max_length=100)
    auto_enviar_ao_criar: bool = False
    testar_conexao: bool = True


def formatar_tamanho(bytes_num: int) -> str:
    val = float(bytes_num)
    for unit in ["B", "KB", "MB", "GB"]:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} TB"


def _criar_snapshot_local() -> dict:
    """Cria um snapshot consistente do SQLite local na pasta backups/."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    db_abs_path = os.path.abspath(db_path)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"escola_artes_backup_{timestamp_str}.db"
    dest_path = os.path.join(BACKUP_DIR, backup_filename)

    if settings.DATABASE_URL.startswith("sqlite") and os.path.exists(db_abs_path):
        src_conn = sqlite3.connect(db_abs_path)
        dest_conn = sqlite3.connect(dest_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()
    else:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write("BACKUP_SNAPSHOT")

    file_size = os.path.getsize(dest_path)
    created_at_str = datetime.now(timezone.utc).isoformat()
    return {
        "arquivo": backup_filename,
        "dest_path": dest_path,
        "tamanho_bytes": file_size,
        "tamanho_formatado": formatar_tamanho(file_size),
        "criado_em": created_at_str,
    }


def _to_remote_status(cfg: dict) -> RemoteConfigStatus:
    return RemoteConfigStatus(
        configurado=cfg["configurado"],
        provedor="supabase",
        supabase_url=cfg.get("supabase_url", ""),
        bucket=cfg.get("bucket", "backups"),
        prefixo=cfg.get("prefixo", "escola-artes"),
        auto_enviar_ao_criar=bool(cfg.get("auto_enviar_ao_criar", False)),
        chave_mascarada=mask_secret(cfg.get("service_role_key")),
        origem=cfg.get("origem", "nao_configurado"),
    )


@router.post(
    "/create",
    response_model=BackupItem,
    status_code=status.HTTP_201_CREATED,
    summary="Criar backup do banco de dados local (com envio remoto opcional)"
)
def create_backup(
    request: Request,
    enviar_remoto: Optional[bool] = Query(None, description="Se true, envia também para o Supabase Storage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    """
    Cria um snapshot do banco de dados SQLite local na pasta de backups.
    Quando `enviar_remoto=true` ou `auto_enviar_ao_criar` estiver ativo, envia também ao Supabase.
    """
    snap = _criar_snapshot_local()
    cfg = carregar_config_remota()
    deve_enviar = enviar_remoto if enviar_remoto is not None else (cfg["configurado"] and cfg["auto_enviar_ao_criar"])

    enviado_remoto = False
    remoto_mensagem: Optional[str] = None
    if deve_enviar:
        try:
            client = get_supabase_client_from_config()
            res = client.upload_file(snap["dest_path"], snap["arquivo"])
            enviado_remoto = True
            remoto_mensagem = f"Enviado para {res['caminho_remoto']}"
        except RemoteBackupError as exc:
            remoto_mensagem = exc.message

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="BACKUP_CRIADO",
        entidade="Backup",
        registro_id=snap["arquivo"],
        detalhes={
            "tamanho_bytes": snap["tamanho_bytes"],
            "enviado_remoto": enviado_remoto,
        },
        usuario=current_user,
        ip=client_ip,
    )

    return BackupItem(
        arquivo=snap["arquivo"],
        tamanho_bytes=snap["tamanho_bytes"],
        tamanho_formatado=snap["tamanho_formatado"],
        criado_em=snap["criado_em"],
        enviado_remoto=enviado_remoto,
        remoto_mensagem=remoto_mensagem,
    )


@router.get(
    "/list",
    response_model=List[BackupItem],
    summary="Listar backups locais disponíveis"
)
def list_backups(
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    if not os.path.exists(BACKUP_DIR):
        return []

    itens = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith(".db") or f.endswith(".bak"):
            full_path = os.path.join(BACKUP_DIR, f)
            size = os.path.getsize(full_path)
            c_time = datetime.fromtimestamp(os.path.getctime(full_path), timezone.utc).isoformat()
            itens.append(BackupItem(
                arquivo=f,
                tamanho_bytes=size,
                tamanho_formatado=formatar_tamanho(size),
                criado_em=c_time
            ))
    return itens


@router.get(
    "/download/{filename}",
    summary="Fazer download de um arquivo de backup local"
)
def download_backup(
    filename: str,
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(BACKUP_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de backup não encontrado.")

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/octet-stream"
    )


# ==================== BACKUP REMOTO (SUPABASE STORAGE) ====================

@router.get(
    "/remote/status",
    response_model=RemoteConfigStatus,
    summary="Consultar status da configuração de backup remoto (Supabase)"
)
def get_remote_backup_status(
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    cfg = carregar_config_remota()
    return _to_remote_status(cfg)


@router.put(
    "/remote/config",
    response_model=RemoteConfigStatus,
    summary="Configurar credenciais do backup remoto no Supabase"
)
def update_remote_backup_config(
    config_in: RemoteConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    try:
        atual = carregar_config_remota()
        chave_efetiva = (config_in.service_role_key or "").strip() or atual.get("service_role_key", "")
        if config_in.testar_conexao:
            client = SupabaseStorageClient(
                supabase_url=config_in.supabase_url,
                service_role_key=chave_efetiva,
                bucket=config_in.bucket,
                prefixo=config_in.prefixo,
            )
            client.ensure_bucket()

        cfg = salvar_config_remota(
            supabase_url=config_in.supabase_url,
            service_role_key=chave_efetiva,
            bucket=config_in.bucket,
            prefixo=config_in.prefixo,
            auto_enviar_ao_criar=config_in.auto_enviar_ao_criar,
        )
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="CONFIGURACAO_BACKUP_REMOTO",
        entidade="BackupRemoto",
        registro_id=cfg["bucket"],
        detalhes={
            "provedor": "supabase",
            "bucket": cfg["bucket"],
            "prefixo": cfg["prefixo"],
            "auto_enviar_ao_criar": cfg["auto_enviar_ao_criar"],
        },
        usuario=current_user,
        ip=client_ip,
    )
    return _to_remote_status(cfg)


@router.post(
    "/remote/test",
    summary="Testar conexão com o Supabase Storage e garantir bucket privado"
)
def test_remote_backup_connection(
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    try:
        client = get_supabase_client_from_config()
        info = client.ensure_bucket()
        return {
            "ok": True,
            "bucket": info["bucket"],
            "criado": info["criado"],
            "mensagem": f"Conexão com Supabase validada (bucket '{info['bucket']}').",
        }
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/remote/sync-now",
    response_model=RemoteBackupItem,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar novo snapshot local e enviar imediatamente para o Supabase"
)
def sync_new_backup_to_remote(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    snap = _criar_snapshot_local()
    try:
        client = get_supabase_client_from_config()
        uploaded = client.upload_file(snap["dest_path"], snap["arquivo"])
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="BACKUP_REMOTO_ENVIADO",
        entidade="BackupRemoto",
        registro_id=uploaded["arquivo"],
        detalhes={
            "caminho_remoto": uploaded["caminho_remoto"],
            "tamanho_bytes": uploaded["tamanho_bytes"],
        },
        usuario=current_user,
        ip=client_ip,
    )

    return RemoteBackupItem(
        arquivo=uploaded["arquivo"],
        caminho_remoto=uploaded["caminho_remoto"],
        tamanho_bytes=uploaded["tamanho_bytes"],
        tamanho_formatado=formatar_tamanho(uploaded["tamanho_bytes"]),
        criado_em=snap["criado_em"],
    )


@router.post(
    "/remote/upload/{filename}",
    response_model=RemoteBackupItem,
    summary="Enviar um backup local existente para o Supabase"
)
def upload_existing_backup_to_remote(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(BACKUP_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de backup local não encontrado.")

    try:
        client = get_supabase_client_from_config()
        uploaded = client.upload_file(file_path, safe_filename)
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="BACKUP_REMOTO_ENVIADO",
        entidade="BackupRemoto",
        registro_id=uploaded["arquivo"],
        detalhes={"caminho_remoto": uploaded["caminho_remoto"], "tamanho_bytes": uploaded["tamanho_bytes"]},
        usuario=current_user,
        ip=client_ip,
    )

    return RemoteBackupItem(
        arquivo=uploaded["arquivo"],
        caminho_remoto=uploaded["caminho_remoto"],
        tamanho_bytes=uploaded["tamanho_bytes"],
        tamanho_formatado=formatar_tamanho(uploaded["tamanho_bytes"]),
        criado_em=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/remote/list",
    response_model=List[RemoteBackupItem],
    summary="Listar backups armazenados no Supabase Storage"
)
def list_remote_backups(
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value, UserRole.COORDENACAO.value))
):
    cfg = carregar_config_remota()
    if not cfg["configurado"]:
        return []

    try:
        client = get_supabase_client_from_config()
        items = client.list_files()
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return [
        RemoteBackupItem(
            arquivo=it["arquivo"],
            caminho_remoto=it["caminho_remoto"],
            tamanho_bytes=it["tamanho_bytes"],
            tamanho_formatado=formatar_tamanho(it["tamanho_bytes"]),
            criado_em=it["criado_em"],
        )
        for it in items
    ]


@router.get(
    "/remote/download/{filename}",
    summary="Baixar um backup diretamente do Supabase Storage"
)
def download_remote_backup(
    filename: str,
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    safe_filename = os.path.basename(filename)
    try:
        client = get_supabase_client_from_config()
        content = client.download_bytes(safe_filename)
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post(
    "/remote/pull/{filename}",
    response_model=BackupItem,
    summary="Copiar um backup remoto do Supabase para a pasta local backups/"
)
def pull_remote_backup_to_local(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    safe_filename = os.path.basename(filename)
    try:
        client = get_supabase_client_from_config()
        content = client.download_bytes(safe_filename)
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest_path = os.path.join(BACKUP_DIR, safe_filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    file_size = os.path.getsize(dest_path)
    created_at_str = datetime.now(timezone.utc).isoformat()

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="BACKUP_REMOTO_BAIXADO_LOCAL",
        entidade="BackupRemoto",
        registro_id=safe_filename,
        detalhes={"tamanho_bytes": file_size},
        usuario=current_user,
        ip=client_ip,
    )

    return BackupItem(
        arquivo=safe_filename,
        tamanho_bytes=file_size,
        tamanho_formatado=formatar_tamanho(file_size),
        criado_em=created_at_str,
        enviado_remoto=True,
        remoto_mensagem="Importado do Supabase para backups locais",
    )


@router.delete(
    "/remote/{filename}",
    summary="Excluir um backup armazenado no Supabase Storage"
)
def delete_remote_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DIRECAO.value))
):
    safe_filename = os.path.basename(filename)
    try:
        client = get_supabase_client_from_config()
        client.delete_file(safe_filename)
    except RemoteBackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        db=db,
        acao="BACKUP_REMOTO_EXCLUIDO",
        entidade="BackupRemoto",
        registro_id=safe_filename,
        detalhes={"arquivo": safe_filename},
        usuario=current_user,
        ip=client_ip,
    )
    return {"mensagem": f"Backup remoto '{safe_filename}' removido do Supabase."}
