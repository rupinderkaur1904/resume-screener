"""
Centralized application configuration, loaded from environment variables / .env file.

pydantic-settings type-checks every value at startup, so a missing SECRET_KEY
or malformed DATABASE_URL fails immediately when the container starts instead
of causing a confusing 500 error three requests later.
"""
from functools import lru_cache
from typing import List, Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "AI Resume Screener"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Database ---
    # Example: postgresql+asyncpg://user:pass@db:5432/resume_screener
    DATABASE_URL: str

    # --- Auth ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- File uploads ---
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_UPLOAD_EXTENSIONS: Tuple[str, ...] = (".pdf",)

    # --- ML ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MODEL_CACHE_DIR: str = "/app/model_cache"

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. Env vars are read once on first call and the same
    object is reused everywhere (main.py, database.py, ml/*) via this function,
    rather than every module re-parsing the environment independently.
    """
    return Settings()