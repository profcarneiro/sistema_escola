import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

BACKUP_DIR = os.path.abspath("backups")
REMOTE_CONFIG_FILE = os.path.join(BACKUP_DIR, ".supabase_config.json")


class RemoteBackupError(Exception):
    """Erro operacional na comunicação com o provedor remoto de backup."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def mask_secret(secret: Optional[str]) -> Optional[str]:
    """Mascara chaves secretas para exibição segura na interface e logs."""
    if not secret:
        return None
    s = secret.strip()
    if len(s) <= 8:
        return "****"
    return f"{s[:4]}...{s[-4:]}"


def validar_supabase_url(url: str) -> str:
    clean = (url or "").strip().rstrip("/")
    if not clean:
        raise RemoteBackupError("A URL do projeto Supabase é obrigatória.", status_code=400)
    if not (
        clean.startswith("https://")
        or clean.startswith("http://localhost")
        or clean.startswith("http://127.0.0.1")
    ):
        raise RemoteBackupError(
            "A URL do Supabase deve usar HTTPS (ex: https://seu-projeto.supabase.co).",
            status_code=400,
        )
    return clean


def sanitizar_segmento(valor: str, padrao: str) -> str:
    clean = (valor or "").strip().strip("/")
    if not clean:
        return padrao
    if not re.match(r"^[a-zA-Z0-9._-]+$", clean):
        raise RemoteBackupError(
            "Bucket e prefixo devem conter apenas letras, números, '-', '_' ou '.'.",
            status_code=400,
        )
    return clean


def carregar_config_remota() -> Dict[str, Any]:
    """
    Carrega a configuração do Supabase Storage.
    Prioriza o arquivo local protegido (`backups/.supabase_config.json`) quando existir,
    fazendo fallback para as variáveis de ambiente em `settings`.
    """
    origem = "nao_configurado"
    cfg: Dict[str, Any] = {
        "supabase_url": (settings.SUPABASE_URL or "").strip().rstrip("/"),
        "service_role_key": (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip(),
        "bucket": (settings.SUPABASE_BACKUP_BUCKET or "backups").strip(),
        "prefixo": (settings.SUPABASE_BACKUP_PREFIX or "escola-artes").strip().strip("/"),
        "auto_enviar_ao_criar": bool(settings.SUPABASE_AUTO_BACKUP_ON_LOCAL),
    }
    if cfg["supabase_url"] and cfg["service_role_key"]:
        origem = "variavel_ambiente"

    if os.path.exists(REMOTE_CONFIG_FILE):
        try:
            with open(REMOTE_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for campo in ("supabase_url", "service_role_key", "bucket", "prefixo"):
                if campo in saved and saved[campo] is not None:
                    cfg[campo] = str(saved[campo]).strip().rstrip("/") if campo in ("supabase_url", "prefixo") else str(saved[campo]).strip()
            if "auto_enviar_ao_criar" in saved:
                cfg["auto_enviar_ao_criar"] = bool(saved["auto_enviar_ao_criar"])
            if cfg["supabase_url"] and cfg["service_role_key"]:
                origem = "arquivo_local"
        except (OSError, json.JSONDecodeError):
            pass

    cfg["origem"] = origem
    cfg["configurado"] = bool(cfg["supabase_url"] and cfg["service_role_key"])
    return cfg


def salvar_config_remota(
    supabase_url: str,
    service_role_key: Optional[str],
    bucket: str = "backups",
    prefixo: str = "escola-artes",
    auto_enviar_ao_criar: bool = False,
) -> Dict[str, Any]:
    atual = carregar_config_remota()
    url_validada = validar_supabase_url(supabase_url)
    chave_final = (service_role_key or "").strip() or atual.get("service_role_key", "")
    if not chave_final:
        raise RemoteBackupError(
            "A Service Role Key do Supabase é obrigatória na primeira configuração.",
            status_code=400,
        )

    bucket_limpo = sanitizar_segmento(bucket, "backups")
    prefixo_limpo = sanitizar_segmento(prefixo, "escola-artes")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    payload = {
        "supabase_url": url_validada,
        "service_role_key": chave_final,
        "bucket": bucket_limpo,
        "prefixo": prefixo_limpo,
        "auto_enviar_ao_criar": bool(auto_enviar_ao_criar),
    }
    with open(REMOTE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    try:
        os.chmod(REMOTE_CONFIG_FILE, 0o600)
    except OSError:
        pass

    return carregar_config_remota()


class SupabaseStorageClient:
    """Cliente REST minimalista para Supabase Storage (sem SDK pesado adicional)."""

    def __init__(self, supabase_url: str, service_role_key: str, bucket: str, prefixo: str = "escola-artes"):
        self.supabase_url = validar_supabase_url(supabase_url)
        self.service_role_key = (service_role_key or "").strip()
        if not self.service_role_key:
            raise RemoteBackupError("Service Role Key do Supabase não configurada.", status_code=400)
        self.bucket = sanitizar_segmento(bucket, "backups")
        self.prefixo = sanitizar_segmento(prefixo, "escola-artes")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    def _object_path(self, filename: str) -> str:
        safe_name = os.path.basename(filename)
        if not safe_name or safe_name != filename or safe_name in (".", ".."):
            raise RemoteBackupError("Nome de arquivo de backup inválido.", status_code=400)
        return f"{self.prefixo}/{safe_name}" if self.prefixo else safe_name

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.supabase_url}{path}"
        headers = {**self._headers, **kwargs.pop("headers", {})}
        try:
            with httpx.Client(timeout=30.0) as client:
                return client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise RemoteBackupError(
                f"Falha de conexão com o servidor Supabase: {exc}",
                status_code=502,
            ) from exc

    def ensure_bucket(self) -> Dict[str, Any]:
        """Verifica acesso ao bucket no Supabase Storage e o cria como privado se ainda não existir."""
        resp = self._request("GET", f"/storage/v1/bucket/{self.bucket}")
        if resp.status_code == 200:
            return {"bucket": self.bucket, "criado": False, "public": resp.json().get("public", False)}

        if resp.status_code in (401, 403):
            raise RemoteBackupError(
                "Credenciais do Supabase rejeitadas (verifique a Service Role Key).",
                status_code=401,
            )

        if resp.status_code in (400, 404):
            create_resp = self._request(
                "POST",
                "/storage/v1/bucket",
                json={"id": self.bucket, "name": self.bucket, "public": False},
            )
            if create_resp.status_code in (200, 201):
                return {"bucket": self.bucket, "criado": True, "public": False}
            if create_resp.status_code == 409:
                return {"bucket": self.bucket, "criado": False, "public": False}
            raise RemoteBackupError(
                f"Não foi possível criar o bucket '{self.bucket}' no Supabase ({create_resp.status_code}): {create_resp.text}",
                status_code=502,
            )

        raise RemoteBackupError(
            f"Erro ao validar bucket no Supabase ({resp.status_code}): {resp.text}",
            status_code=502,
        )

    def upload_file(self, local_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        if not os.path.exists(local_path):
            raise RemoteBackupError("Arquivo local de backup não encontrado para envio.", status_code=404)

        self.ensure_bucket()
        target_name = os.path.basename(filename or local_path)
        object_path = self._object_path(target_name)

        with open(local_path, "rb") as f:
            data = f.read()

        resp = self._request(
            "POST",
            f"/storage/v1/object/{self.bucket}/{object_path}",
            headers={"Content-Type": "application/octet-stream", "x-upsert": "true"},
            content=data,
        )
        if resp.status_code not in (200, 201):
            raise RemoteBackupError(
                f"Falha ao enviar backup para o Supabase ({resp.status_code}): {resp.text}",
                status_code=502,
            )

        return {
            "arquivo": target_name,
            "caminho_remoto": f"{self.bucket}/{object_path}",
            "tamanho_bytes": len(data),
        }

    def list_files(self) -> List[Dict[str, Any]]:
        resp = self._request(
            "POST",
            f"/storage/v1/object/list/{self.bucket}",
            json={
                "prefix": self.prefixo,
                "limit": 100,
                "offset": 0,
                "sortBy": {"column": "created_at", "order": "desc"},
            },
        )
        if resp.status_code in (400, 404):
            # Bucket ainda inexistente -> retorna lista vazia
            return []
        if resp.status_code in (401, 403):
            raise RemoteBackupError(
                "Credenciais do Supabase inválidas para listar backups.",
                status_code=401,
            )
        if resp.status_code != 200:
            raise RemoteBackupError(
                f"Erro ao listar backups no Supabase ({resp.status_code}): {resp.text}",
                status_code=502,
            )

        items = resp.json() if isinstance(resp.json(), list) else []
        backups: List[Dict[str, Any]] = []
        for item in items:
            nome = item.get("name") or ""
            if not nome.endswith((".db", ".bak", ".sqlite")):
                continue
            metadata = item.get("metadata") or {}
            size = int(metadata.get("size") or 0)
            created = item.get("created_at") or item.get("updated_at") or ""
            backups.append({
                "arquivo": nome,
                "caminho_remoto": f"{self.bucket}/{self._object_path(nome)}",
                "tamanho_bytes": size,
                "criado_em": created,
            })
        return backups

    def download_bytes(self, filename: str) -> bytes:
        object_path = self._object_path(filename)
        resp = self._request("GET", f"/storage/v1/object/{self.bucket}/{object_path}")
        if resp.status_code in (400, 404):
            raise RemoteBackupError("Backup remoto não encontrado no Supabase.", status_code=404)
        if resp.status_code != 200:
            raise RemoteBackupError(
                f"Erro ao baixar backup do Supabase ({resp.status_code}): {resp.text}",
                status_code=502,
            )
        return resp.content

    def delete_file(self, filename: str) -> None:
        object_path = self._object_path(filename)
        resp = self._request(
            "DELETE",
            f"/storage/v1/object/{self.bucket}",
            json={"prefixes": [object_path]},
        )
        if resp.status_code not in (200, 204):
            raise RemoteBackupError(
                f"Erro ao excluir backup remoto no Supabase ({resp.status_code}): {resp.text}",
                status_code=502,
            )


def get_supabase_client_from_config() -> SupabaseStorageClient:
    cfg = carregar_config_remota()
    if not cfg["configurado"]:
        raise RemoteBackupError(
            "Backup remoto (Supabase) não configurado. Informe a URL do projeto e a Service Role Key.",
            status_code=400,
        )
    return SupabaseStorageClient(
        supabase_url=cfg["supabase_url"],
        service_role_key=cfg["service_role_key"],
        bucket=cfg["bucket"],
        prefixo=cfg["prefixo"],
    )
