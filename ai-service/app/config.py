"""AI Service application configuration (Team B).

Reads environment variables with sane defaults (a local ``ai-service/.env`` is loaded
when python-dotenv is installed). Avoids a hard dependency on ``pydantic-settings``
so the service stays runnable on minimal images.

LLM usage is opt-in by key: when ``GEMINI_API_KEY`` (or ``OPENAI_API_KEY``) is set,
``MOCK_AI_MODE`` defaults to ``false`` and the model is used ONLY to write labels and
narrative. Every financial number still comes from the deterministic engine.
"""

import os

from functools import lru_cache
from pathlib import Path

_SERVICE_DIR = Path(__file__).resolve().parent.parent

try:  # optional: load ai-service/.env so a Gemini key can live outside the shell
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(_SERVICE_DIR / ".env")
except Exception:  # pragma: no cover
    pass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Typed-ish settings sourced from the environment."""

    def __init__(self) -> None:
        # Application
        self.APP_NAME: str = os.getenv("APP_NAME", "AI Credit Underwriter - AI Service")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = _as_bool(os.getenv("DEBUG"), True)

        # Server
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8100"))

        # AI provider (Gemini free tier preferred, OpenAI-compatible fallback)
        self.GEMINI_API_KEY: str | None = (os.getenv("GEMINI_API_KEY") or "").strip() or None
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.OPENAI_API_KEY: str | None = (os.getenv("OPENAI_API_KEY") or "").strip() or None
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        self.LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
        self.LLM_MAX_OUTPUT_TOKENS: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024"))

        # When true, deterministic/rule-based engines run WITHOUT any LLM call (₹0 mode).
        # Default: mock unless an API key is configured.
        raw_mock = os.getenv("MOCK_AI_MODE")
        if raw_mock is None:
            self.MOCK_AI_MODE: bool = not bool(self.GEMINI_API_KEY or self.OPENAI_API_KEY)
        else:
            self.MOCK_AI_MODE = _as_bool(raw_mock, True)

        # Policy
        self.POLICY_PROFILE: str = os.getenv("POLICY_PROFILE", "default")
        self.POLICY_PATH: str = os.getenv("POLICY_PATH", str(_SERVICE_DIR / "policies"))

        # Persistence (SQLite by default for zero-config; Postgres via DATABASE_URL in prod)
        default_db = _SERVICE_DIR / "data" / "ai_service.db"
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{default_db.as_posix()}",
        )

        # Deterministic risk scoring backend: auto | xgboost | fallback
        self.RISK_BACKEND: str = os.getenv("RISK_BACKEND", "auto")

    @property
    def llm_provider(self) -> str:
        """Which provider will answer LLM calls: ``mock`` | ``gemini`` | ``openai``."""
        if self.MOCK_AI_MODE:
            return "mock"
        if self.GEMINI_API_KEY:
            return "gemini"
        if self.OPENAI_API_KEY:
            return "openai"
        return "mock"

    @property
    def llm_model(self) -> str | None:
        provider = self.llm_provider
        if provider == "gemini":
            return self.GEMINI_MODEL
        if provider == "openai":
            return self.OPENAI_MODEL
        return None

    def policy_file(self, profile: str | None = None) -> Path:
        return Path(self.POLICY_PATH) / f"{profile or self.POLICY_PROFILE}.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
