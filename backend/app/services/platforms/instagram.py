"""Instagram platform service."""

from __future__ import annotations

import asyncio

import httpx

from app.services.platforms.base import BasePlatformService
from app.exceptions import PlatformError

_BASE = "https://graph.instagram.com/v19.0"
_MAX_REEL_POLL_ATTEMPTS = 12
_REEL_POLL_INTERVAL_S = 5


class InstagramService(BasePlatformService):
    platform_name = "instagram"

    def __init__(self, access_token: str, user_id: str) -> None:
        self._token = access_token
        self._uid = user_id

    async def post_image(self, image_url: str, caption: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                container = await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._uid}/media",
                    params={"image_url": image_url, "caption": caption, "access_token": self._token},
                )
                return await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._uid}/media_publish",
                    params={"creation_id": container["id"], "access_token": self._token},
                )
            except Exception as exc:
                raise self._wrap_error(exc, "post_image")

    async def post_reel(self, video_url: str, caption: str) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                container = await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._uid}/media",
                    params={
                        "media_type": "REELS",
                        "video_url": video_url,
                        "caption": caption,
                        "access_token": self._token,
                    },
                )
                container_id = container["id"]

                # Poll until processing completes
                for _ in range(_MAX_REEL_POLL_ATTEMPTS):
                    await asyncio.sleep(_REEL_POLL_INTERVAL_S)
                    status_resp = await client.get(
                        f"{_BASE}/{container_id}",
                        params={"fields": "status_code", "access_token": self._token},
                    )
                    if status_resp.json().get("status_code") == "FINISHED":
                        break

                return await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._uid}/media_publish",
                    params={"creation_id": container_id, "access_token": self._token},
                )
            except PlatformError:
                raise
            except Exception as exc:
                raise self._wrap_error(exc, "post_reel")
