#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização em Comando Único — Escola de Artes Helena Barufaldi
# ==============================================================================
set -e

# Garante que a execução ocorra no diretório raiz do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Verifica ou cria o ambiente virtual Python se não existir ou estiver incompleto
if [ ! -f "venv/bin/python" ]; then
    echo "📦 Criando ambiente virtual em ./venv..."
    python3 -m venv venv
fi

# 2. Garante que o pip está disponível no ambiente virtual
if [ ! -f "venv/bin/pip" ]; then
    echo "⚙️  Instalando pip no ambiente virtual..."
    ./venv/bin/python -m ensurepip --default-pip 2>/dev/null || python3 -m ensurepip 2>/dev/null || true
fi

# 3. Verifica se as dependências essenciais (ex: uvicorn) estão instaladas
if [ ! -f "venv/bin/uvicorn" ]; then
    echo "📦 Instalando dependências a partir do requirements.txt..."
    ./venv/bin/python -m pip install --upgrade pip
    ./venv/bin/python -m pip install -r requirements.txt
    echo "✅ Dependências instaladas com sucesso!"
fi

# 4. Inicia o sistema unificado (Backend + Frontend)
exec ./venv/bin/python run.py "$@"
