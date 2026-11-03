#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização em Comando Único — Escola de Artes Helena Barufaldi
# ==============================================================================
set -e

# Garante que a execução ocorra no diretório raiz do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Verifica ou cria o ambiente virtual Python se não existir
if [ ! -d "venv" ]; then
    echo "📦 Ambiente virtual não encontrado. Criando em ./venv..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# 2. Inicia o sistema unificado (Backend + Frontend)
exec ./venv/bin/python run.py "$@"
