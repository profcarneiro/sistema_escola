# ==============================================================================
# Dockerfile Multi-Stage — Escola de Artes Helena Barufaldi
# ==============================================================================

# --- Etapa 1: Build do Frontend React / Vite ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Etapa 2: Servidor Python / FastAPI ---
FROM python:3.13-slim AS production

# Instala bibliotecas do sistema para compilação e PostgreSQL se necessário
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código do backend e scripts de execução
COPY backend/ ./backend/
COPY run.py .

# Copia os arquivos compilados do frontend gerados na Etapa 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Cria diretório para backups locais temporários
RUN mkdir -p backups

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV ENVIRONMENT=production
ENV PORT=8080

EXPOSE 8080

# Health check para orquestradores (Render / Docker)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando de inicialização
CMD ["python", "run.py"]
