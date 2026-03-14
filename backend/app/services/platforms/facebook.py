"""Facebook platform service."""

from __future__ import annotations

import httpx

from app.services.platforms.base import BasePlatformService
from app.exceptions import PlatformError

_BASE = "https://graph.facebook.com/v19.0"
_MAX_CAPTION = 63_206


class FacebookService(BasePlatformService):
    platform_name = "facebook"

    def __init__(self, access_token: str, page_id: str) -> None:
        self._token = access_token
        self._page_id = page_id

    async def post_text(self, message: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                return await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._page_id}/feed",
                    params={"message": message[:_MAX_CAPTION], "access_token": self._token},
                )
            except Exception as exc:
                raise self._wrap_error(exc, "post_text")

    async def post_photo(self, image_url: str, caption: str) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                return await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._page_id}/photos",
                    params={"url": image_url, "caption": caption, "access_token": self._token},
                )
            except Exception as exc:
                raise self._wrap_error(exc, "post_photo")

    async def post_video(self, video_url: str, description: str, title: str = "") -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                return await self._post_with_retry(
                    client,
                    f"{_BASE}/{self._page_id}/videos",
                    params={
                        "file_url": video_url,
                        "description": description,
                        "title": title,
                        "access_token": self._token,
                    },
                )
            except Exception as exc:
                raise self._wrap_error(exc, "post_video")
