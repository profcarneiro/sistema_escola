from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import engine, Base, SessionLocal
from app.initial_data import init_db
from app.routers import (
    auth_router,
    users_router,
    lgpd_router,
    rooms_router,
    courses_router,
    teachers_router,
    class_groups_router,
    students_router,
    enrollments_router,
    attendance_router,
)





@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da aplicação: inicializa banco e dados padrão na inicialização."""
    # Cria todas as tabelas no banco de dados se não existirem
    Base.metadata.create_all(bind=engine)

    # Executa a carga inicial do usuário administrador da escola
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API de Gestão da Escola de Artes Helena Barufaldi — Nova Odessa/SP. "
        "Módulos de Autenticação RBAC, Gestão de Usuários, Auditoria e Conformidade LGPD."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configuração de CORS para aplicações frontend locais
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores da API v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(lgpd_router, prefix=settings.API_V1_STR)
app.include_router(rooms_router, prefix=settings.API_V1_STR)
app.include_router(courses_router, prefix=settings.API_V1_STR)
app.include_router(teachers_router, prefix=settings.API_V1_STR)
app.include_router(class_groups_router, prefix=settings.API_V1_STR)
app.include_router(students_router, prefix=settings.API_V1_STR)
app.include_router(enrollments_router, prefix=settings.API_V1_STR)
app.include_router(attendance_router, prefix=settings.API_V1_STR)





@app.get("/", tags=["Status"])
def root():
    """Boas-vindas e identificação da API da Escola de Artes Helena Barufaldi."""
    return {
        "sistema": settings.PROJECT_NAME,
        "versao": settings.VERSION,
        "status": "operacional",
        "documentacao": f"{settings.API_V1_STR}/docs",
        "cidade": "Nova Odessa - SP"
    }


@app.get("/health", tags=["Status"])
def health_check():
    """Health check para monitoramento do serviço."""
    return {"status": "ok", "mensagem": "Servidor em execução normal."}
