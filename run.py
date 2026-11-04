#!/usr/bin/env python3
"""
Ponto de entrada único para o Sistema de Gestão da Escola de Artes Helena Barufaldi.
Inicia o servidor backend FastAPI e serve a aplicação Web completa em http://localhost:8000.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório 'backend' ao PYTHONPATH automaticamente
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    is_prod = os.environ.get("RENDER") is not None or os.environ.get("ENVIRONMENT", "").lower() == "production"

    print("\n" + "=" * 68)
    print(" 🎨 ESCOLA DE ARTES HELENA BARUFALDI — SISTEMA DE GESTÃO")
    print("=" * 68)
    print(f" 🌐 Servidor ativo na porta: {port}")
    print(f" 📖 Documentação da API:     /api/v1/docs")
    print(" 🔑 Usuário Administrador:   admin@hbartes.com")
    print(" 🔒 Senha Inicial:           admin123")
    print("=" * 68)
    if not is_prod:
        print(" ⚠️  IMPORTANTE (Local): Acesse com HTTP comum (sem o 's'):")
        print(f"    👉 http://localhost:{port} ou http://<IP_DO_SERVIDOR>:{port}")
        print("=" * 68)
    print(" Servidor pronto para conexões.\n")

    uvicorn.run("app.main:app", host=host, port=port, reload=not is_prod)
