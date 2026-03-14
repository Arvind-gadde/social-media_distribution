"""Application configuration — validated at startup, never at request time."""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Redis (self-hosted or Upstash) ────────────────────────────────────
    # Upstash: rediss://default:<password>@<host>.upstash.io:6380
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # ── Token Encryption ─────────────────────────────────────────────────
    TOKEN_ENCRYPTION_KEY: str

    # ── OAuth — Google Login ──────────────────────────────────────────────
    # IMPORTANT: This must point to the FRONTEND callback page, not the backend.
    # Register http://localhost:5173/auth/callback in Google Cloud Console.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/callback"

    # ── Object Storage — Cloudflare R2 ────────────────────────────────────
    # R2 is S3-compatible. Get values from:
    # dash.cloudflare.com → R2 → Manage R2 API Tokens
    # S3_ENDPOINT_URL format: https://<account-id>.r2.cloudflarestorage.com
    # S3_PUBLIC_BASE_URL: set after enabling public access on the bucket
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "contentflow-media"
    S3_REGION: str = "auto"  # R2 uses "auto"
    S3_PUBLIC_BASE_URL: str = ""

    # ── AI — Primary: Gemini, Fallback: OpenAI ───────────────────────────
    # Gemini free tier: 1,500 req/day. Get key at aistudio.google.com
    GEMINI_API_KEY: str = ""
    # OpenAI as backup. Get key at platform.openai.com
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
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.APP_ALLOWED_ORIGINS.split(",")]

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_any_ai(self) -> bool:
        return self.has_gemini or self.has_openai

    @property
    def has_s3(self) -> bool:
        return bool(self.S3_ACCESS_KEY_ID and self.S3_SECRET_ACCESS_KEY)

    # ── Startup validation ────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        insecure = {"CHANGE-ME", "changeme", "secret", ""}
        for field_name in ("APP_SECRET_KEY", "JWT_SECRET_KEY"):
            value = getattr(self, field_name, "")
            if any(value.lower().startswith(s) for s in insecure):
                if self.is_production:
                    raise ValueError(
                        f"{field_name} must be set to a secure value in production. "
                        "Generate with: openssl rand -hex 64"
                    )
        if self.is_production and not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required in production")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton. Call get_settings() everywhere."""
    return Settings()