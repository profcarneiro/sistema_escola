from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Escola de Artes Helena Barufaldi"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Segurança e Autenticação
    SECRET_KEY: str = "escola_artes_helena_barufaldi_secret_key_prod_change_2026_super_secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # Banco de Dados
    DATABASE_URL: str = "sqlite:///./escola_artes.db"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Administrador Padrão (Seed)
    FIRST_SUPERUSER_EMAIL: str = "admin@hbartes.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"
    FIRST_SUPERUSER_NAME: str = "Helena Barufaldi (Direção)"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
