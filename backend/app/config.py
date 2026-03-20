"""Application configuration — validated at startup, never at request time."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to this file so it works regardless of CWD.
# Supports both: running uvicorn from project root OR from backend/.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # ── Dev bypass ────────────────────────────────────────────────────────
    DEV_BYPASS_AUTH: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # ── Token Encryption ─────────────────────────────────────────────────
    TOKEN_ENCRYPTION_KEY: str

    # ── OAuth — Google Login ──────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/callback"

    # ── Object Storage — Cloudflare R2 ────────────────────────────────────
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "contentflow-media"
    S3_REGION: str = "auto"
    S3_PUBLIC_BASE_URL: str = ""

    # ── AI ────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Platforms ─────────────────────────────────────────────────────────
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""

    # ── Push Notifications ────────────────────────────────────────────────
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "admin@contentflow.app"

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.APP_ALLOWED_ORIGINS.split(",")]

    @property
    def has_anthropic(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_any_ai(self) -> bool:
        return self.has_anthropic or self.has_gemini or self.has_openai

    @property
    def has_s3(self) -> bool:
        return bool(self.S3_ACCESS_KEY_ID and self.S3_SECRET_ACCESS_KEY)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        url = str(value).strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        elif url.startswith("postgresql+psycopg2://"):
            url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
        return url

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        insecure = {"CHANGE-ME", "changeme", "secret", ""}
        for field_name in ("APP_SECRET_KEY", "JWT_SECRET_KEY"):
            value = getattr(self, field_name, "")
            if any(value.lower() == s for s in insecure):
                if self.is_production:
                    raise ValueError(
                        f"{field_name} must be set to a secure value in production."
                    )
        if self.is_production and not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required in production")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — one instance per process lifetime."""
    return Settings()
