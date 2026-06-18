"""Tests for the YouTube resumable upload and TikTok publish adapters.

httpx network calls are stubbed via ``unittest.mock.patch`` so the tests do
not touch the real platform APIs.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.platforms.adapters import (
    PublishPayload,
    YouTubeAdapter,
    TikTokAdapter,
)


def _mock_response(status_code: int, *, json_data: dict | None = None, headers: dict | None = None, content: bytes = b"", text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.content = content
    resp.text = text or ""
    return resp


def _video_payload(**overrides) -> PublishPayload:
    defaults = {
        "caption": "Hello world",
        "hashtags": ["AI"],
        "media_urls": ["https://cdn.example/v.mp4"],
        "media_type": "video",
    }
    defaults.update(overrides)
    return PublishPayload(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────────────────────────────────────


class TestYouTubeAdapter:
    @pytest.mark.asyncio
    async def test_rejects_non_video_payload(self):
        adapter = YouTubeAdapter("token")
        result = await adapter.publish(
            PublishPayload(caption="t", hashtags=[], media_urls=[], media_type="text")
        )
        assert result.success is False
        assert result.failure_class == "invalid_media"
        assert result.retryable is False

    @pytest.mark.asyncio
    async def test_rejects_missing_media_urls(self):
        adapter = YouTubeAdapter("token")
        result = await adapter.publish(
            PublishPayload(caption="t", hashtags=[], media_urls=[], media_type="video")
        )
        assert result.success is False
        assert result.failure_class == "no_video_provided"

    @pytest.mark.asyncio
    async def test_successful_resumable_upload(self):
        adapter = YouTubeAdapter("token")

        source = _mock_response(
            200,
            content=b"VIDEO_BYTES_42",
            headers={"content-type": "video/mp4"},
        )
        init = _mock_response(
            200,
            headers={"Location": "https://upload.example/session"},
            json_data={},
        )
        upload = _mock_response(
            200,
            json_data={"id": "abc123", "kind": "youtube#video"},
        )

        client = MagicMock()
        client.get = AsyncMock(return_value=source)
        client.post = AsyncMock(return_value=init)
        client.put = AsyncMock(return_value=upload)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is True
        assert result.platform_post_id == "abc123"
        assert result.platform_post_url == "https://www.youtube.com/watch?v=abc123"
        assert result.provider_response_code == 200

        # Init call must declare resumable upload + carry metadata.
        init_kwargs = client.post.call_args.kwargs
        assert init_kwargs["params"]["uploadType"] == "resumable"
        assert "snippet" in init_kwargs["json"]
        assert init_kwargs["headers"]["X-Upload-Content-Length"] == str(len(b"VIDEO_BYTES_42"))

    @pytest.mark.asyncio
    async def test_session_init_503_is_retryable(self):
        adapter = YouTubeAdapter("token")

        source = _mock_response(200, content=b"X", headers={"content-type": "video/mp4"})
        init = _mock_response(503, text="upstream busy")

        client = MagicMock()
        client.get = AsyncMock(return_value=source)
        client.post = AsyncMock(return_value=init)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.retryable is True
        assert result.failure_class == "server_error"
        assert result.provider_response_code == 503

    @pytest.mark.asyncio
    async def test_session_init_401_marks_auth_failure(self):
        adapter = YouTubeAdapter("token")

        source = _mock_response(200, content=b"X", headers={"content-type": "video/mp4"})
        init = _mock_response(401, text="token expired")

        client = MagicMock()
        client.get = AsyncMock(return_value=source)
        client.post = AsyncMock(return_value=init)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.retryable is False
        assert result.failure_class == "auth"

    @pytest.mark.asyncio
    async def test_missing_upload_url_is_retryable(self):
        adapter = YouTubeAdapter("token")

        source = _mock_response(200, content=b"X", headers={"content-type": "video/mp4"})
        init = _mock_response(200, headers={})  # No Location header

        client = MagicMock()
        client.get = AsyncMock(return_value=source)
        client.post = AsyncMock(return_value=init)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.failure_class == "missing_upload_url"
        assert result.retryable is True

    @pytest.mark.asyncio
    async def test_source_download_failure_marked_unretryable_on_4xx(self):
        adapter = YouTubeAdapter("token")
        source = _mock_response(404, text="not found")

        client = MagicMock()
        client.get = AsyncMock(return_value=source)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.failure_class == "source_fetch_failed"
        assert result.retryable is False
        assert result.provider_response_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# TikTok
# ─────────────────────────────────────────────────────────────────────────────


class TestTikTokAdapter:
    @pytest.mark.asyncio
    async def test_rejects_non_video(self):
        adapter = TikTokAdapter("token")
        result = await adapter.publish(
            PublishPayload(caption="t", hashtags=[], media_urls=[], media_type="text")
        )
        assert result.success is False
        assert result.failure_class == "invalid_media"

    @pytest.mark.asyncio
    async def test_publish_success_uses_pull_from_url(self):
        adapter = TikTokAdapter("token", platform_username="creator")
        init = _mock_response(
            200,
            json_data={"data": {"publish_id": "pub-42"}, "error": {"code": "ok"}},
        )

        client = MagicMock()
        client.post = AsyncMock(return_value=init)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is True
        assert result.platform_post_id == "pub-42"
        assert result.platform_post_url == "https://www.tiktok.com/@creator"

        body = client.post.call_args.kwargs["json"]
        assert body["source_info"]["source"] == "PULL_FROM_URL"
        assert body["source_info"]["video_url"] == "https://cdn.example/v.mp4"
        assert body["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"

    @pytest.mark.asyncio
    async def test_publish_rate_limit_is_retryable(self):
        adapter = TikTokAdapter("token")
        resp = _mock_response(
            429,
            json_data={"error": {"code": "rate_limit_exceeded", "message": "slow down"}},
        )

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.retryable is True
        assert result.failure_class == "rate_limited"

    @pytest.mark.asyncio
    async def test_publish_invalid_token_not_retryable(self):
        adapter = TikTokAdapter("token")
        resp = _mock_response(
            401,
            json_data={"error": {"code": "access_token_invalid", "message": "expired"}},
        )

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_video_payload())

        assert result.success is False
        assert result.retryable is False
        assert result.failure_class == "auth"
