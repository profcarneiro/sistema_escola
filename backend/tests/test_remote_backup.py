import os
import pytest

from app.routers import backup as backup_router
from app.services import remote_backup


@pytest.fixture
def isolated_backup_env(tmp_path, monkeypatch):
    """Isola diretório de backups, arquivo de credenciais e store em memória para simular o Supabase."""
    bkp_dir = str(tmp_path / "backups")
    os.makedirs(bkp_dir, exist_ok=True)
    cfg_file = os.path.join(bkp_dir, ".supabase_config.json")

    monkeypatch.setattr(remote_backup, "BACKUP_DIR", bkp_dir)
    monkeypatch.setattr(remote_backup, "REMOTE_CONFIG_FILE", cfg_file)
    monkeypatch.setattr(backup_router, "BACKUP_DIR", bkp_dir)

    storage: dict[str, bytes] = {}

    class FakeSupabaseClient:
        def __init__(self, supabase_url, service_role_key, bucket, prefixo="escola-artes"):
            self.supabase_url = remote_backup.validar_supabase_url(supabase_url)
            self.service_role_key = service_role_key
            self.bucket = remote_backup.sanitizar_segmento(bucket, "backups")
            self.prefixo = remote_backup.sanitizar_segmento(prefixo, "escola-artes")

        def ensure_bucket(self):
            return {"bucket": self.bucket, "criado": False, "public": False}

        def upload_file(self, local_path, filename=None):
            name = os.path.basename(filename or local_path)
            with open(local_path, "rb") as f:
                data = f.read()
            key = f"{self.prefixo}/{name}" if self.prefixo else name
            storage[key] = data
            return {
                "arquivo": name,
                "caminho_remoto": f"{self.bucket}/{key}",
                "tamanho_bytes": len(data),
            }

        def list_files(self):
            items = []
            for key, data in sorted(storage.items(), reverse=True):
                name = os.path.basename(key)
                items.append({
                    "arquivo": name,
                    "caminho_remoto": f"{self.bucket}/{key}",
                    "tamanho_bytes": len(data),
                    "criado_em": "2026-11-15T14:00:00Z",
                })
            return items

        def download_bytes(self, filename):
            safe = os.path.basename(filename)
            key = f"{self.prefixo}/{safe}" if self.prefixo else safe
            if key not in storage:
                raise remote_backup.RemoteBackupError("Backup remoto não encontrado.", status_code=404)
            return storage[key]

        def delete_file(self, filename):
            safe = os.path.basename(filename)
            key = f"{self.prefixo}/{safe}" if self.prefixo else safe
            storage.pop(key, None)

    monkeypatch.setattr(backup_router, "SupabaseStorageClient", FakeSupabaseClient)
    monkeypatch.setattr(
        backup_router,
        "get_supabase_client_from_config",
        lambda: FakeSupabaseClient(
            **{
                k: remote_backup.carregar_config_remota()[k]
                for k in ("supabase_url", "service_role_key", "bucket", "prefixo")
            }
        ) if remote_backup.carregar_config_remota()["configurado"] else (_ for _ in ()).throw(
            remote_backup.RemoteBackupError("Backup remoto não configurado.", status_code=400)
        ),
    )

    return {"storage": storage, "backup_dir": bkp_dir, "config_file": cfg_file}


def deve_rejeitar_url_http_nao_local_e_mascarar_chave_no_status(client, admin_token, isolated_backup_env):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Rejeita URL sem HTTPS
    bad_resp = client.put("/api/v1/backup/remote/config", json={
        "supabase_url": "http://meuprojeto.supabase.co",
        "service_role_key": "sb_secret_1234567890",
        "bucket": "backups"
    }, headers=headers)
    assert bad_resp.status_code == 400

    # Salva configuração válida
    ok_resp = client.put("/api/v1/backup/remote/config", json={
        "supabase_url": "https://escolatest.supabase.co",
        "service_role_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.chave_super_secreta_9876",
        "bucket": "backups-escola",
        "prefixo": "producao",
        "auto_enviar_ao_criar": True
    }, headers=headers)
    assert ok_resp.status_code == 200
    data = ok_resp.json()
    assert data["configurado"] is True
    assert data["bucket"] == "backups-escola"
    assert data["auto_enviar_ao_criar"] is True
    assert "chave_super_secreta" not in str(data)
    assert data["chave_mascarada"].startswith("eyJh")
    assert data["chave_mascarada"].endswith("9876")

    # Consulta status posteriormente sem expor a chave real
    status_resp = client.get("/api/v1/backup/remote/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["configurado"] is True
    assert "chave_super_secreta" not in status_resp.text


def deve_sincronizar_listar_baixar_e_importar_backup_remoto_supabase(client, admin_token, isolated_backup_env):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Configura Supabase mockado
    cfg_resp = client.put("/api/v1/backup/remote/config", json={
        "supabase_url": "https://escolatest.supabase.co",
        "service_role_key": "sb_secret_abcdef123456",
        "bucket": "backups",
        "prefixo": "escola-artes",
        "auto_enviar_ao_criar": False
    }, headers=headers)
    assert cfg_resp.status_code == 200

    # 1) Sincronização imediata gera snapshot e envia ao Supabase
    sync_resp = client.post("/api/v1/backup/remote/sync-now", headers=headers)
    assert sync_resp.status_code == 201
    sync_data = sync_resp.json()
    filename = sync_data["arquivo"]
    assert filename.endswith(".db")
    assert sync_data["caminho_remoto"] == f"backups/escola-artes/{filename}"
    assert f"escola-artes/{filename}" in isolated_backup_env["storage"]

    # 2) Listagem remota retorna o snapshot
    list_resp = client.get("/api/v1/backup/remote/list", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["arquivo"] == filename for item in list_resp.json())

    # 3) Download direto da nuvem
    dl_resp = client.get(f"/api/v1/backup/remote/download/{filename}", headers=headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == isolated_backup_env["storage"][f"escola-artes/{filename}"]

    # 4) Remove arquivo local e importa de volta do Supabase via pull
    local_file = os.path.join(isolated_backup_env["backup_dir"], filename)
    os.remove(local_file)
    assert not os.path.exists(local_file)

    pull_resp = client.post(f"/api/v1/backup/remote/pull/{filename}", headers=headers)
    assert pull_resp.status_code == 200
    assert os.path.exists(local_file)

    # 5) Create local com enviar_remoto=true também envia ao Supabase
    auto_resp = client.post("/api/v1/backup/create?enviar_remoto=true", headers=headers)
    assert auto_resp.status_code == 201
    assert auto_resp.json()["enviado_remoto"] is True

    # 6) Exclusão remota
    del_resp = client.delete(f"/api/v1/backup/remote/{filename}", headers=headers)
    assert del_resp.status_code == 200
    assert f"escola-artes/{filename}" not in isolated_backup_env["storage"]


def deve_restringir_configuracao_e_sync_remoto_para_perfil_nao_direcao(
    client, secretaria_token, professor_token, isolated_backup_env
):
    for tok in (secretaria_token, professor_token):
        headers = {"Authorization": f"Bearer {tok}"}
        res_cfg = client.put("/api/v1/backup/remote/config", json={
            "supabase_url": "https://escolatest.supabase.co",
            "service_role_key": "sb_secret_123456789"
        }, headers=headers)
        assert res_cfg.status_code == 403

        res_sync = client.post("/api/v1/backup/remote/sync-now", headers=headers)
        assert res_sync.status_code == 403
