"""Application settings loaded from environment/.env (Phase 2.1).

Fail-fast on missing required vars. Secrets never hardcoded (rules Part B).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from env vars / `.env` — never from code."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Auth
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # LLM (API-only; used from Phase 10 onward)
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-flash-latest", alias="GEMINI_MODEL")

    # Email (Resend; used from Phase 27 onward)
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    email_from: str = Field(default="onboarding@resend.dev", alias="EMAIL_FROM")

    # Storage / web
    storage_path: str = Field(default="./uploads", alias="STORAGE_PATH")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")

    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy-engine-ready URL (Phase 0/1 decision: no Docker).

        - Plain `postgresql://...` (Neon) is rewritten to the psycopg3 driver.
        - `sqlite://` URLs pass through untouched (unit tests).
        """
        url = self.database_url
        if url.startswith("postgresql+"):
            return url
        if url.startswith("postgresql"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — use this, don't instantiate Settings ad hoc.

    mypy can't see that pydantic-settings fills required fields from env;
    the ignore is load-bearing for the fail-fast required-vars pattern.
    """
    return Settings()  # type: ignore[call-arg]
