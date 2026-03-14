"""Cache service — thin async Redis wrapper with typed helpers."""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CacheService:
    """Async Redis wrapper. Injected as a dependency — not a global singleton."""

    def __init__(self) -> None:
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        try:
            await self._redis.setex(key, ttl_seconds, json.dumps(value))
        except Exception as exc:
            logger.warning("cache_set_failed", key=key, error=str(exc))

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = await self._redis.get(key)
            return json.loads(data) if data else None
        except Exception as exc:
            logger.warning("cache_get_failed", key=key, error=str(exc))
            return None

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception as exc:
            logger.warning("cache_delete_failed", key=key, error=str(exc))

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._redis.exists(key))
        except Exception:
            return False

    # ── Typed helpers ─────────────────────────────────────────────────────

    async def blacklist_jti(self, jti: str, ttl_seconds: int) -> None:
        await self.set(f"jti_blacklist:{jti}", True, ttl_seconds)

    async def is_jti_blacklisted(self, jti: str) -> bool:
        return await self.exists(f"jti_blacklist:{jti}")

    async def cache_user(self, user_id: str, data: dict, ttl_seconds: int = 1800) -> None:
        await self.set(f"user:{user_id}", data, ttl_seconds)

    async def get_cached_user(self, user_id: str) -> Optional[dict]:
        return await self.get(f"user:{user_id}")

    async def invalidate_user(self, user_id: str) -> None:
        await self.delete(f"user:{user_id}")

    async def save_push_subscription(self, user_id: str, sub: dict) -> None:
        await self.set(f"push_sub:{user_id}", sub, ttl_seconds=86400 * 30)

    async def get_push_subscription(self, user_id: str) -> Optional[dict]:
        return await self.get(f"push_sub:{user_id}")


# Module-level instance used in workers (where DI isn't available)
_cache: Optional[CacheService] = None


def get_cache_instance() -> CacheService:
    global _cache
    if _cache is None:
        _cache = CacheService()
    return _cache
