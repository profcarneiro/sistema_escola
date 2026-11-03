#!/usr/bin/env python3
"""
Ponto de entrada único para o Sistema de Gestão da Escola de Artes Helena Barufaldi.
Inicia o servidor backend FastAPI e serve a aplicação Web completa em http://localhost:8000.
"""
import sys
from pathlib import Path

# Adiciona o diretório 'backend' ao PYTHONPATH automaticamente
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 68)
    print(" 🎨 ESCOLA DE ARTES HELENA BARUFALDI — SISTEMA DE GESTÃO LOCAL")
    print("=" * 68)
    print(" 🌐 Aplicação Web Completa:  http://localhost:8000")
    print(" 📖 Documentação da API:    http://localhost:8000/api/v1/docs")
    print(" 🔑 Usuário Administrador:   admin@hbartes.com")
    print(" 🔒 Senha Inicial:           admin123")
    print("=" * 68)
    print(" Pressione CTRL+C para encerrar o servidor.\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
