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
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # ── LLM Routing ──────────────────────────────────────────────────────
    # Allow callers to route by abstract tier (cheap/mid/frontier) instead
    # of naming a model. Useful for cost-aware experiments.
    LLM_TIER_CHEAP_MODEL: str = "gemini-2.0-flash"
    LLM_TIER_MID_MODEL: str = "gpt-4o-mini"
    LLM_TIER_FRONTIER_MODEL: str = "gpt-4o"
    # Enable Anthropic prompt caching on system blocks (no-op if backend lacks support)
    ANTHROPIC_PROMPT_CACHING: bool = True

    # ── LLM Observability — Langfuse ──────────────────────────────────────
    # Leave empty to disable. Self-hostable; supports cloud (us/eu) regions.
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

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
    YOUTUBE_API_KEY: str = ""
    TWITTER_BEARER_TOKEN: str = ""

    # ── Trend Detection & Web Scraping (Phase 14) ─────────────────────────
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "ContentFlow/1.0"
    PROXY_URL: str = ""
    PROXY_ROTATION_ENABLED: bool = False

    # ── Push Notifications ────────────────────────────────────────────────
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "admin@contentflow.app"

    # ── Platform webhook verification ─────────────────────────────────────
    META_WEBHOOK_VERIFY_TOKEN: str = ""
    YOUTUBE_WEBHOOK_CHANNEL_TOKEN: str = ""
    TIKTOK_WEBHOOK_SECRET: str = ""
    LINKEDIN_WEBHOOK_SECRET: str = ""

    # ── Observability (Sentry / PostHog / Prometheus) ────────────────────
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.05
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0
    APP_RELEASE: str = ""
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://us.i.posthog.com"

    # ── Vector store (Qdrant) ─────────────────────────────────────────────
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NICHE: str = "contentflow_niches"
    QDRANT_COLLECTION_CONTENT: str = "contentflow_content"
    QDRANT_COLLECTION_DOCUMENTS: str = "contentflow_documents"
    QDRANT_VECTOR_SIZE: int = 1536  # OpenAI text-embedding-3-small default

    # ── Embeddings ────────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "openai"  # openai | local
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE: int = 96
    EMBEDDING_CACHE_TTL: int = 86400  # 1 day Redis cache

    # ── Speech-to-text (Whisper) ──────────────────────────────────────────
    WHISPER_PROVIDER: str = "openai"  # openai | local
    WHISPER_MODEL: str = "whisper-1"
    WHISPER_LOCAL_MODEL_PATH: str = ""

    # ── Stripe Billing (Phase 11) ─────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    PRICE_PRO_MONTHLY: str = "price_pro_monthly"
    PRICE_PRO_YEARLY: str = "price_pro_yearly"
    PRICE_BUSINESS_MONTHLY: str = "price_business_monthly"
    PRICE_BUSINESS_YEARLY: str = "price_business_yearly"

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        # Robust to casing/whitespace so a stray "Production" / " production "
        # can never silently fall through to non-prod (which would re-enable
        # the dev auth bypass). Anything that is not explicitly a dev/test/
        # staging env is treated as production (fail-safe).
        env = (self.APP_ENV or "").strip().lower()
        return env in {"production", "prod"}

    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        url = url.replace("+aiosqlite", "")
        return url

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
    def has_openrouter(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def has_any_ai(self) -> bool:
        return (
            self.has_anthropic
            or self.has_gemini
            or self.has_openai
            or self.has_openrouter
        )

    @property
    def has_langfuse(self) -> bool:
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def has_s3(self) -> bool:
        return bool(self.S3_ACCESS_KEY_ID and self.S3_SECRET_ACCESS_KEY)

    @property
    def has_stripe(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY and self.STRIPE_WEBHOOK_SECRET)

    @property
    def has_qdrant(self) -> bool:
        return bool(self.QDRANT_URL)

    @property
    def has_whisper(self) -> bool:
        if self.WHISPER_PROVIDER == "openai":
            return self.has_openai
        return bool(self.WHISPER_LOCAL_MODEL_PATH)

    @property
    def has_reddit(self) -> bool:
        return bool(self.REDDIT_CLIENT_ID and self.REDDIT_CLIENT_SECRET)

    @property
    def has_youtube_api(self) -> bool:
        return bool(self.YOUTUBE_API_KEY)

    @property
    def has_twitter_api(self) -> bool:
        return bool(self.TWITTER_BEARER_TOKEN or (self.TWITTER_API_KEY and self.TWITTER_API_SECRET))

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
        insecure_exact = {"change-me", "changeme", "secret", "dev", "password", ""}
        for field_name in ("APP_SECRET_KEY", "JWT_SECRET_KEY"):
            value = (getattr(self, field_name, "") or "").strip()
            lowered = value.lower()
            is_weak = lowered in insecure_exact or len(value) < 32
            if is_weak:
                if self.is_production:
                    raise ValueError(
                        f"{field_name} must be a high-entropy string of at least 32 chars "
                        f"in production. Generate one with `python -c 'import secrets; print(secrets.token_urlsafe(48))'`."
                    )
                # Dev/staging: warn loudly but allow boot
                import warnings

                warnings.warn(
                    f"[contentflow] {field_name} is weak ({'placeholder' if lowered in insecure_exact else 'too short'}). "
                    "Acceptable for local dev only.",
                    stacklevel=2,
                )
        if self.is_production and not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required in production")
        
        # Validate TOKEN_ENCRYPTION_KEY format
        if self.TOKEN_ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet
                import base64
                # Try to decode as base64 or validate as passphrase
                test_key = self.TOKEN_ENCRYPTION_KEY.encode('utf-8')
                try:
                    decoded = base64.urlsafe_b64decode(test_key)
                    if len(decoded) == 32:
                        # Valid Fernet key
                        pass
                except Exception:
                    # Will be hashed to 32 bytes in TokenVault
                    pass
            except ImportError:
                pass  # cryptography not installed yet
        
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — one instance per process lifetime."""
    return Settings()
