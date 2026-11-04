@echo off
REM ==============================================================================
REM Script de Inicializacao no Windows — Escola de Artes Helena Barufaldi
REM ==============================================================================

cd /d %~dp0

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [INFO] Criando ambiente virtual Python em venv...
    python -m venv venv
)

call venv\Scripts\activate.bat

IF NOT EXIST "venv\Scripts\uvicorn.exe" (
    echo [INFO] Instalando dependencias a partir do requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [INFO] Iniciando o Sistema de Gestao da Escola de Artes Helena Barufaldi...
python run.py

pause
