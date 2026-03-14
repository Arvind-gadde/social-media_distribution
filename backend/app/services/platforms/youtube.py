"""YouTube platform service."""

from __future__ import annotations

import json

import httpx

from app.services.platforms.base import BasePlatformService
from app.exceptions import PlatformError

_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_BOUNDARY = "contentflow_boundary_v1"


class YouTubeService(BasePlatformService):
    platform_name = "youtube"

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def upload_video(
        self,
        video_bytes: bytes,
        title: str,
        description: str,
        tags: list[str] | None = None,
        is_short: bool = False,
    ) -> dict:
        tags = tags or []
        if is_short:
            tags.append("#Shorts")

        metadata = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        }

        body = (
            f"--{_BOUNDARY}\r\nContent-Type: application/json\r\n\r\n".encode()
            + json.dumps(metadata).encode()
            + f"\r\n--{_BOUNDARY}\r\nContent-Type: video/*\r\n\r\n".encode()
            + video_bytes
            + f"\r\n--{_BOUNDARY}--".encode()
        )

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{_UPLOAD_URL}?uploadType=multipart&part=snippet,status",
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": f"multipart/related; boundary={_BOUNDARY}",
                    },
                    content=body,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise self._wrap_error(exc, "upload_video")
