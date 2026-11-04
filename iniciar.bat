@echo off
REM ==============================================================================
REM Script de Inicializacao no Windows — Escola de Artes Helena Barufaldi
REM ==============================================================================

cd /d %~dp0

IF NOT EXIST "venv" (
    echo [INFO] Criando ambiente virtual Python...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo [INFO] Iniciando o Sistema de Gestao da Escola de Artes Helena Barufaldi...
python run.py

pause
