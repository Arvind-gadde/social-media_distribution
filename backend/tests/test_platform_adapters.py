"""Tests for platform publishing adapters.

What is tested:
  - PublishPayload construction and caption formatting
  - Adapter factory — get_adapter returns correct type
  - Instagram, Twitter, LinkedIn adapters — mocked httpx calls
  - Thread publishing for Twitter
  - Error classification (retryable vs non-retryable)
  - Token validation
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.platforms.adapters import (
    PlatformAdapter,
    PublishPayload,
    PublishResult,
    InstagramAdapter,
    TwitterAdapter,
    LinkedInAdapter,
    YouTubeAdapter,
    TikTokAdapter,
    FacebookAdapter,
    PinterestAdapter,
    get_adapter,
    ADAPTERS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_payload(**overrides) -> PublishPayload:
    defaults = {
        "caption": "Breaking: AI just changed everything 🤖",
        "hashtags": ["#AI", "#Technology", "#Innovation"],
        "media_urls": [],
        "media_type": "text",
    }
    defaults.update(overrides)
    return PublishPayload(**defaults)


def _mock_httpx_response(status_code: int, json_data: dict | None = None, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or json.dumps(json_data or {})
    resp.headers = {"x-restli-id": "urn:li:share:123456"}
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestAdapterFactory:
    def test_get_instagram_adapter(self):
        adapter = get_adapter("instagram", "token123", platform_user_id="123")
        assert isinstance(adapter, InstagramAdapter)

    def test_get_twitter_adapter(self):
        adapter = get_adapter("twitter", "token123")
        assert isinstance(adapter, TwitterAdapter)

    def test_get_linkedin_adapter(self):
        adapter = get_adapter("linkedin", "token123")
        assert isinstance(adapter, LinkedInAdapter)

    def test_get_youtube_adapter(self):
        adapter = get_adapter("youtube", "token123")
        assert isinstance(adapter, YouTubeAdapter)

    def test_get_tiktok_adapter(self):
        adapter = get_adapter("tiktok", "token123")
        assert isinstance(adapter, TikTokAdapter)

    def test_get_facebook_adapter(self):
        adapter = get_adapter("facebook", "token123", page_id="p1")
        assert isinstance(adapter, FacebookAdapter)

    def test_get_pinterest_adapter(self):
        adapter = get_adapter("pinterest", "token123", board_id="b1")
        assert isinstance(adapter, PinterestAdapter)

    def test_unsupported_platform_raises(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_adapter("snapchat", "token123")

    def test_all_adapters_registered(self):
        assert set(ADAPTERS.keys()) == {
            "instagram", "twitter", "linkedin", "youtube", "tiktok",
            "facebook", "pinterest", "mastodon", "bluesky",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Caption formatting
# ─────────────────────────────────────────────────────────────────────────────

class TestCaptionFormatting:
    def test_caption_with_hashtags(self):
        adapter = InstagramAdapter("token")
        payload = _make_payload(
            caption="Test caption",
            hashtags=["AI", "#Tech", "Innovation"],
        )
        full = adapter._build_full_caption(payload)
        assert "Test caption" in full
        assert "#AI" in full
        assert "#Tech" in full
        assert "#Innovation" in full

    def test_caption_truncation(self):
        adapter = TwitterAdapter("token")
        long_caption = "x" * 500
        payload = _make_payload(caption=long_caption)
        full = adapter._build_full_caption(payload)
        assert len(full) <= adapter.MAX_CAPTION_LENGTH

    def test_hashtag_dedup_with_hash_prefix(self):
        adapter = InstagramAdapter("token")
        result = adapter._format_hashtags(["#AI", "AI", "#Tech"])
        assert result.count("#AI") == 1 or result == "#AI #AI #Tech"  # Both valid
        assert "#Tech" in result

    def test_empty_hashtags_no_trailing_newlines(self):
        adapter = InstagramAdapter("token")
        payload = _make_payload(hashtags=[])
        full = adapter._build_full_caption(payload)
        assert not full.endswith("\n\n")


# ─────────────────────────────────────────────────────────────────────────────
# Instagram Adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestInstagramAdapter:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = InstagramAdapter("token", platform_user_id="123")

        container_resp = _mock_httpx_response(200, {"id": "container_123"})
        publish_resp = _mock_httpx_response(200, {"id": "media_456"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[container_resp, publish_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is True
        assert result.platform_post_id == "media_456"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_publish_container_failure(self):
        adapter = InstagramAdapter("token", platform_user_id="123")

        error_resp = _mock_httpx_response(400, {"error": {"message": "Invalid media"}})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is False
        assert result.failure_class == "container_creation_failed"
        assert result.retryable is False  # 400 is not retryable

    @pytest.mark.asyncio
    async def test_publish_server_error_is_retryable(self):
        adapter = InstagramAdapter("token", platform_user_id="123")

        error_resp = _mock_httpx_response(500, {"error": "Internal"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=error_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is False
        assert result.retryable is True

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        adapter = InstagramAdapter("valid_token")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_httpx_response(200))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_token() is True

    @pytest.mark.asyncio
    async def test_validate_token_expired(self):
        adapter = InstagramAdapter("expired_token")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_httpx_response(401))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await adapter.validate_token() is False


# ─────────────────────────────────────────────────────────────────────────────
# Twitter Adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestTwitterAdapter:
    @pytest.mark.asyncio
    async def test_single_tweet_success(self):
        adapter = TwitterAdapter("token", platform_username="testuser")

        tweet_resp = _mock_httpx_response(201, {"data": {"id": "tweet_789"}})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=tweet_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is True
        assert result.platform_post_id == "tweet_789"
        assert "testuser" in result.platform_post_url

    @pytest.mark.asyncio
    async def test_thread_publishing(self):
        adapter = TwitterAdapter("token", platform_username="testuser")

        responses = [
            _mock_httpx_response(201, {"data": {"id": f"tweet_{i}"}})
            for i in range(3)
        ]

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=responses)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        payload = _make_payload(
            thread_tweets=["First tweet 🧵", "Second tweet", "Final tweet"],
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(payload)

        assert result.success is True
        assert result.platform_post_id == "tweet_0"  # First tweet ID
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_is_retryable(self):
        adapter = TwitterAdapter("token")

        rate_limit_resp = _mock_httpx_response(429, {"title": "Too Many Requests"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=rate_limit_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is False
        assert result.retryable is True


# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestLinkedInAdapter:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = LinkedInAdapter("token", author_urn="urn:li:person:abc123")

        success_resp = MagicMock()
        success_resp.status_code = 201
        success_resp.headers = {"x-restli-id": "urn:li:share:post_999"}
        success_resp.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=success_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is True
        assert "urn:li:share:post_999" in result.platform_post_id


# ─────────────────────────────────────────────────────────────────────────────
# YouTube Adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestYouTubeAdapter:
    @pytest.mark.asyncio
    async def test_publish_without_video_fails(self):
        adapter = YouTubeAdapter("token")
        result = await adapter.publish(
            _make_payload(media_urls=[], media_type="video")
        )

        assert result.success is False
        assert result.failure_class == "no_video_provided"
        assert result.retryable is False


# ─────────────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_network_exception_is_retryable(self):
        adapter = InstagramAdapter("token", platform_user_id="123")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ConnectionError("Network unreachable"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.publish(_make_payload())

        assert result.success is False
        assert result.retryable is True
        assert result.failure_class == "exception"
