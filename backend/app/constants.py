"""Application-wide constants. No magic numbers anywhere else in the codebase."""

from __future__ import annotations

# ── Media Constraints ─────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
ALLOWED_MIME_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB read chunks

# ── Platform Character Limits ─────────────────────────────────────────────
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "instagram": 2200,
    "facebook": 63_206,
    "youtube": 5_000,
    "youtube_shorts": 5_000,
    "linkedin": 3_000,
    "x": 280,
    "josh": 200,
    "moj": 200,
    "koo": 400,
    "sharechat": 500,
    "chingari": 200,
    "roposo": 200,
}

# ── Platform Video Specs ──────────────────────────────────────────────────
PLATFORM_VIDEO_SPECS: dict[str, dict] = {
    "instagram": {"max_size_mb": 100, "max_duration_s": 90, "resolution": "1080x1920", "fps": 30},
    "youtube": {"max_size_mb": 256_000, "max_duration_s": None, "resolution": None, "fps": None},
    "youtube_shorts": {"max_size_mb": 256, "max_duration_s": 60, "resolution": "1080x1920", "fps": 60},
    "facebook": {"max_size_mb": 4_096, "max_duration_s": 240, "resolution": "1920x1080", "fps": 30},
    "linkedin": {"max_size_mb": 5_120, "max_duration_s": 600, "resolution": "1920x1080", "fps": 30},
    "x": {"max_size_mb": 512, "max_duration_s": 140, "resolution": "1280x720", "fps": 40},
    "josh": {"max_size_mb": 50, "max_duration_s": 60, "resolution": "1080x1920", "fps": 30},
    "moj": {"max_size_mb": 50, "max_duration_s": 30, "resolution": "1080x1920", "fps": 30},
}

# ── Platform Hashtags ─────────────────────────────────────────────────────
PLATFORM_DEFAULT_HASHTAGS: dict[str, list[str]] = {
    "instagram": ["#Instagram", "#Reels", "#IndianCreator", "#ContentCreator"],
    "youtube": ["#YouTube", "#Subscribe", "#NewVideo"],
    "youtube_shorts": ["#Shorts", "#YouTubeShorts", "#ViralShorts"],
    "linkedin": [],
    "x": ["#India", "#Trending"],
    "facebook": [],
    "josh": ["#Josh", "#JoshApp", "#IndianContent"],
    "moj": ["#Moj", "#MojApp", "#MojCreator"],
    "koo": ["#Koo", "#KooApp"],
    "sharechat": ["#ShareChat"],
    "chingari": ["#Chingari"],
    "roposo": ["#Roposo"],
}

# ── Indian Regional Languages ─────────────────────────────────────────────
INDIA_REGIONAL_LANGUAGE_CODES = frozenset({"hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"})

# ── Celery ────────────────────────────────────────────────────────────────
CELERY_DISTRIBUTION_QUEUE = "distribution"
CELERY_MAX_RETRIES = 3
CELERY_RETRY_BACKOFF_S = 60

# ── Cache TTLs (seconds) ──────────────────────────────────────────────────
CACHE_TTL_USER = 1_800       # 30 min
CACHE_TTL_ANALYTICS = 300    # 5 min
CACHE_TTL_SHORT = 60         # 1 min

# ── Rate Limits ───────────────────────────────────────────────────────────
RATE_LOGIN = "5/minute"
RATE_UPLOAD = "10/minute"
RATE_AI = "20/minute"
RATE_DEFAULT = "60/minute"

# ── Supported AI Tones ────────────────────────────────────────────────────
SUPPORTED_TONES = frozenset({"casual", "professional", "funny", "inspirational", "educational"})
SUPPORTED_LANGUAGES = frozenset({"en", "hi", "ta", "te", "bn", "mr", "gu"})
