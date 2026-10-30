from app.models.audit import AuditLog


def deve_gravar_log_de_auditoria_em_login_sucesso(client, db_session):
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hbartes.com", "senha": "admin123"}
    )
    logs = db_session.query(AuditLog).filter(AuditLog.acao == "LOGIN_SUCESSO").all()
    assert len(logs) >= 1
    assert logs[-1].usuario_email == "admin@hbartes.com"


def deve_gravar_log_de_auditoria_em_login_falha(client, db_session):
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hbartes.com", "senha": "senha_erradissima"}
    )
    logs = db_session.query(AuditLog).filter(AuditLog.acao == "LOGIN_FALHA").all()
    assert len(logs) >= 1
    assert "admin@hbartes.com" in logs[-1].detalhes
    # Garante que a senha errada digitada não é salva nos logs
    assert "senha_erradissima" not in logs[-1].detalhes


def deve_ocultar_senhas_e_credenciais_nos_detalhes_de_auditoria(client, admin_token, db_session):
    client.post(
        "/api/v1/users/",
        json={
            "nome": "Auditoria Teste",
            "email": "audit.test@hbartes.com",
            "role": "Secretaria",
            "ativo": True,
            "senha": "super_secret_password"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    logs = db_session.query(AuditLog).filter(AuditLog.acao == "USUARIO_CRIADO").all()
    assert len(logs) >= 1
    detalhe = logs[-1].detalhes
    assert "super_secret_password" not in detalhe


def deve_gravar_log_em_consentimento_lgpd(client, secretaria_token, db_session):
    client.post(
        "/api/v1/lgpd/consentimentos",
        json={
            "titular_nome": "Juliana Auditoria",
            "titular_tipo": "ALUNO",
            "menor_idade": False,
            "termo_tipo": "GERAL",
            "consentido": True
        },
        headers={"Authorization": f"Bearer {secretaria_token}"}
    )
    logs = db_session.query(AuditLog).filter(AuditLog.acao == "LGPD_CONSENTIMENTO_REGISTRADO").all()
    assert len(logs) >= 1
    assert "Juliana Auditoria" in logs[-1].detalhes
