"""Application configuration loaded from the environment (Team A).

Uses ``pydantic-settings`` when installed; otherwise falls back to a plain
environment reader with the same attribute names so the service still boots on a
minimal image.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = "sqlite:///" + (_BACKEND_DIR / "data" / "backend.db").as_posix()
_DEFAULT_UPLOADS = str(_BACKEND_DIR / "data" / "uploads")


def _split_csv(value: object) -> list[str]:
    if isinstance(value, str):
        return [o.strip() for o in value.split(",") if o.strip()]
    if isinstance(value, list):
        return [str(o) for o in value]
    return ["http://localhost:3000"]


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


try:  # preferred: typed settings with .env support
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):  # type: ignore[misc]
        """Typed settings sourced from environment variables / .env file."""

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

        # Application
        APP_NAME: str = "AI Credit Underwriter - Backend"
        APP_ENV: str = "development"
        DEBUG: bool = True
        SECRET_KEY: str = "change-me-in-production"

        # Server
        HOST: str = "0.0.0.0"
        PORT: int = 8000

        # Database: SQLite for zero-config local demo; Postgres (Supabase) in prod via env
        DATABASE_URL: str = _DEFAULT_DB

        # AI Service (Team B / replaceable REST service)
        AI_SERVICE_URL: str = "http://localhost:8100"
        AI_SERVICE_TIMEOUT: float = 90.0
        # true -> canned responses (Team A dev without Team B); false -> real AI service
        MOCK_AI_MODE: bool = False

        # Auth: demo login (any non-empty email/password unless DEMO_* are set) or Supabase JWT
        DEMO_AUTH: bool = True
        DEMO_USER_EMAIL: str | None = None
        DEMO_USER_PASSWORD: str | None = None
        SUPABASE_URL: str | None = None
        SUPABASE_ANON_KEY: str | None = None
        SUPABASE_SERVICE_ROLE_KEY: str | None = None
        SUPABASE_JWT_SECRET: str | None = None

        # Storage: local folder by default; S3/Supabase bucket name kept for prod wiring
        STORAGE_BACKEND: str = "local"
        STORAGE_BUCKET: str = "documents"
        UPLOAD_DIR: str = _DEFAULT_UPLOADS
        MAX_UPLOAD_MB: int = 10
        ALLOWED_UPLOAD_EXTENSIONS: list[str] = ["pdf", "png", "jpg", "jpeg", "txt"]

        # CORS
        CORS_ORIGINS: list[str] = ["http://localhost:3000"]

        @field_validator("CORS_ORIGINS", "ALLOWED_UPLOAD_EXTENSIONS", mode="before")
        @classmethod
        def _split(cls, value: object) -> object:
            if isinstance(value, str):
                return [o.strip() for o in value.split(",") if o.strip()]
            return value

except Exception:  # pragma: no cover - pydantic-settings not installed

    class Settings:  # type: ignore[no-redef]
        """Plain environment reader with the same attributes as the typed settings."""

        def __init__(self) -> None:
            g = os.getenv
            self.APP_NAME = g("APP_NAME", "AI Credit Underwriter - Backend")
            self.APP_ENV = g("APP_ENV", "development")
            self.DEBUG = _as_bool(g("DEBUG"), True)
            self.SECRET_KEY = g("SECRET_KEY", "change-me-in-production")
            self.HOST = g("HOST", "0.0.0.0")
            self.PORT = int(g("PORT", "8000"))
            self.DATABASE_URL = g("DATABASE_URL", _DEFAULT_DB)
            self.AI_SERVICE_URL = g("AI_SERVICE_URL", "http://localhost:8100")
            self.AI_SERVICE_TIMEOUT = float(g("AI_SERVICE_TIMEOUT", "90"))
            self.MOCK_AI_MODE = _as_bool(g("MOCK_AI_MODE"), False)
            self.DEMO_AUTH = _as_bool(g("DEMO_AUTH"), True)
            self.DEMO_USER_EMAIL = g("DEMO_USER_EMAIL")
            self.DEMO_USER_PASSWORD = g("DEMO_USER_PASSWORD")
            self.SUPABASE_URL = g("SUPABASE_URL")
            self.SUPABASE_ANON_KEY = g("SUPABASE_ANON_KEY")
            self.SUPABASE_SERVICE_ROLE_KEY = g("SUPABASE_SERVICE_ROLE_KEY")
            self.SUPABASE_JWT_SECRET = g("SUPABASE_JWT_SECRET")
            self.STORAGE_BACKEND = g("STORAGE_BACKEND", "local")
            self.STORAGE_BUCKET = g("STORAGE_BUCKET", "documents")
            self.UPLOAD_DIR = g("UPLOAD_DIR", _DEFAULT_UPLOADS)
            self.MAX_UPLOAD_MB = int(g("MAX_UPLOAD_MB", "10"))
            self.ALLOWED_UPLOAD_EXTENSIONS = _split_csv(g("ALLOWED_UPLOAD_EXTENSIONS", "pdf,png,jpg,jpeg,txt"))
            self.CORS_ORIGINS = _split_csv(g("CORS_ORIGINS", "http://localhost:3000"))


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()
