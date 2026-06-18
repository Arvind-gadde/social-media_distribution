"""Tests for Facebook + Pinterest publishing adapters."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.platforms.adapters import (
    FacebookAdapter,
    PinterestAdapter,
    PublishPayload,
)


def _mock_response(status_code: int, *, json_data: dict | None = None, text: str = "", headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or ""
    resp.headers = headers or {}
    return resp


def _payload(**overrides) -> PublishPayload:
    defaults = {
        "caption": "Test post",
        "hashtags": ["AI"],
        "media_urls": [],
        "media_type": "text",
    }
    defaults.update(overrides)
    return PublishPayload(**defaults)


# ─── Facebook ──────────────────────────────────────────────────────────────


class TestFacebookAdapter:
    @pytest.mark.asyncio
    async def test_feed_post_success(self):
        adapter = FacebookAdapter("token", page_id="page-1")
        resp = _mock_response(200, json_data={"id": "page-1_42"})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is True
        assert result.platform_post_id == "page-1_42"
        endpoint, _ = client.post.call_args.args, client.post.call_args.kwargs
        assert "/page-1/feed" in client.post.call_args.args[0]

    @pytest.mark.asyncio
    async def test_image_post_uses_photos_endpoint(self):
        adapter = FacebookAdapter("token", page_id="page-1")
        resp = _mock_response(200, json_data={"post_id": "page-1_99", "id": "99"})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload(
                media_type="image", media_urls=["https://cdn.example/i.jpg"]
            ))

        assert result.success is True
        assert result.platform_post_id == "page-1_99"
        assert "/page-1/photos" in client.post.call_args.args[0]

    @pytest.mark.asyncio
    async def test_missing_page_id_fails_fast(self):
        adapter = FacebookAdapter("token")
        result = await adapter.publish(_payload())
        assert result.success is False
        assert result.failure_class == "missing_page_id"
        assert result.retryable is False

    @pytest.mark.asyncio
    async def test_oauth_error_marked_auth(self):
        adapter = FacebookAdapter("token", page_id="p")
        resp = _mock_response(401, json_data={"error": {"code": 190, "message": "Invalid OAuth"}})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is False
        assert result.failure_class == "auth"
        assert result.retryable is False

    @pytest.mark.asyncio
    async def test_rate_limit_retryable(self):
        adapter = FacebookAdapter("token", page_id="p")
        resp = _mock_response(429, json_data={"error": {"code": 4, "message": "Application request limit reached"}})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.failure_class == "rate_limited"
        assert result.retryable is True


# ─── Pinterest ─────────────────────────────────────────────────────────────


class TestPinterestAdapter:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = PinterestAdapter("token", board_id="board-1")
        resp = _mock_response(201, json_data={"id": "pin-42"})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload(
                media_type="image", media_urls=["https://cdn.example/i.jpg"]
            ))

        assert result.success is True
        assert result.platform_post_id == "pin-42"
        assert result.platform_post_url == "https://www.pinterest.com/pin/pin-42/"
        body = client.post.call_args.kwargs["json"]
        assert body["board_id"] == "board-1"
        assert body["media_source"]["source_type"] == "image_url"

    @pytest.mark.asyncio
    async def test_missing_board_id_fails(self):
        adapter = PinterestAdapter("token")
        result = await adapter.publish(_payload(
            media_type="image", media_urls=["https://cdn.example/i.jpg"]
        ))
        assert result.success is False
        assert result.failure_class == "missing_board_id"

    @pytest.mark.asyncio
    async def test_no_media_fails(self):
        adapter = PinterestAdapter("token", board_id="b")
        result = await adapter.publish(_payload())
        assert result.success is False
        assert result.failure_class == "no_media_provided"

    @pytest.mark.asyncio
    async def test_auth_failure_not_retryable(self):
        adapter = PinterestAdapter("token", board_id="b")
        resp = _mock_response(401, json_data={"code": 2, "message": "Invalid token"})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload(
                media_type="image", media_urls=["https://cdn.example/i.jpg"]
            ))

        assert result.failure_class == "auth"
        assert result.retryable is False

    @pytest.mark.asyncio
    async def test_server_error_retryable(self):
        adapter = PinterestAdapter("token", board_id="b")
        resp = _mock_response(503, json_data={})

        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload(
                media_type="image", media_urls=["https://cdn.example/i.jpg"]
            ))

        assert result.failure_class == "server_error"
        assert result.retryable is True
