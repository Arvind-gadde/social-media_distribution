"""Push notification service — web push via pywebpush."""

from __future__ import annotations

import json

import structlog

from app.config import get_settings
from app.services.cache_service import CacheService

logger = structlog.get_logger(__name__)
settings = get_settings()


class NotificationService:
    def __init__(self, cache: CacheService) -> None:
        self._cache = cache

    async def save_subscription(self, user_id: str, endpoint: str, keys: dict) -> None:
        await self._cache.save_push_subscription(
            user_id, {"endpoint": endpoint, "keys": keys}
        )
        logger.info("push_subscription_saved", user_id=user_id)

    async def remove_subscription(self, user_id: str) -> None:
        await self._cache.delete(f"push_sub:{user_id}")

    async def send(self, user_id: str, title: str, body: str) -> None:
        sub = await self._cache.get_push_subscription(user_id)
        if not sub:
            return

        if not settings.VAPID_PRIVATE_KEY:
            logger.warning("push_skipped_no_vapid", user_id=user_id)
            return

        try:
            from pywebpush import webpush, WebPushException

            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_EMAIL}"},
            )
            logger.info("push_sent", user_id=user_id, title=title)
        except Exception as exc:
            logger.warning("push_failed", user_id=user_id, error=str(exc))
