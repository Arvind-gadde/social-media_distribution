"""Tests for Mastodon + Bluesky publishing adapters."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.platforms.adapters import (
    BlueskyAdapter,
    MastodonAdapter,
    PublishPayload,
    get_adapter,
)


def _mock_response(status_code: int, *, json_data: dict | None = None, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or ""
    return resp


def _client(**methods):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    for name, val in methods.items():
        setattr(client, name, val)
    return client


def _payload(**overrides) -> PublishPayload:
    defaults = {"caption": "Hello fediverse", "hashtags": ["AI"], "media_type": "text"}
    defaults.update(overrides)
    return PublishPayload(**defaults)


# ─── Factory ──────────────────────────────────────────────────────────────────


def test_factory_returns_new_adapters():
    assert isinstance(
        get_adapter("mastodon", "tok", base_url="https://m.example"), MastodonAdapter
    )
    assert isinstance(
        get_adapter("bluesky", "pw", platform_username="a.bsky.social"), BlueskyAdapter
    )


# ─── Mastodon ───────────────────────────────────────────────────────────────


class TestMastodonAdapter:
    @pytest.mark.asyncio
    async def test_publish_success_with_idempotency_header(self):
        adapter = MastodonAdapter("token", base_url="https://mastodon.social")
        resp = _mock_response(
            200, json_data={"id": "12345", "url": "https://mastodon.social/@u/12345"}
        )
        client = _client(post=AsyncMock(return_value=resp))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is True
        assert result.platform_post_id == "12345"
        assert result.platform_post_url == "https://mastodon.social/@u/12345"
        # Posts to the instance statuses endpoint with native idempotency header.
        assert "/api/v1/statuses" in client.post.call_args.args[0]
        assert "Idempotency-Key" in client.post.call_args.kwargs["headers"]

    @pytest.mark.asyncio
    async def test_missing_instance_is_non_retryable(self):
        adapter = MastodonAdapter("token")  # no base_url
        result = await adapter.publish(_payload())
        assert result.success is False
        assert result.failure_class == "missing_instance"
        assert result.retryable is False

    @pytest.mark.asyncio
    async def test_server_error_is_retryable(self):
        adapter = MastodonAdapter("token", base_url="https://mastodon.social")
        resp = _mock_response(503, text="upstream down")
        client = _client(post=AsyncMock(return_value=resp))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is False
        assert result.retryable is True
        assert result.provider_response_code == 503

    @pytest.mark.asyncio
    async def test_client_error_not_retryable(self):
        adapter = MastodonAdapter("token", base_url="https://mastodon.social")
        resp = _mock_response(401, text="unauthorized")
        client = _client(post=AsyncMock(return_value=resp))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is False
        assert result.retryable is False


# ─── Bluesky ────────────────────────────────────────────────────────────────


class TestBlueskyAdapter:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = BlueskyAdapter(
            "app-password", platform_username="alice.bsky.social",
            platform_user_id="did:plc:abc",
        )
        session_resp = _mock_response(
            200, json_data={"accessJwt": "jwt", "did": "did:plc:abc", "handle": "alice.bsky.social"}
        )
        session_resp.raise_for_status = MagicMock()  # no-op on success
        record_resp = _mock_response(
            200, json_data={"uri": "at://did:plc:abc/app.bsky.feed.post/xyz", "cid": "cid1"}
        )
        client = _client(post=AsyncMock(side_effect=[session_resp, record_resp]))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is True
        assert result.platform_post_id == "at://did:plc:abc/app.bsky.feed.post/xyz"
        assert result.platform_post_url == "https://bsky.app/profile/alice.bsky.social/post/xyz"
        # Two calls: createSession then createRecord.
        assert client.post.call_count == 2
        assert "createSession" in client.post.call_args_list[0].args[0]
        assert "createRecord" in client.post.call_args_list[1].args[0]

    @pytest.mark.asyncio
    async def test_auth_failure_classified(self):
        adapter = BlueskyAdapter("bad-password", platform_username="alice.bsky.social")
        req = httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.server.createSession")
        bad = httpx.Response(401, request=req, json={"error": "AuthenticationRequired"})
        client = _client(post=AsyncMock(return_value=bad))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload())

        assert result.success is False
        assert result.failure_class == "bluesky_auth_failed"
        assert result.provider_response_code == 401

    @pytest.mark.asyncio
    async def test_caption_truncated_to_300(self):
        adapter = BlueskyAdapter("pw", platform_username="a.bsky.social")
        long_caption = "x" * 500
        session_resp = _mock_response(200, json_data={"accessJwt": "j", "did": "did:plc:a", "handle": "a.bsky.social"})
        session_resp.raise_for_status = MagicMock()
        record_resp = _mock_response(200, json_data={"uri": "at://did:plc:a/app.bsky.feed.post/k", "cid": "c"})
        client = _client(post=AsyncMock(side_effect=[session_resp, record_resp]))

        with patch("httpx.AsyncClient", return_value=client):
            result = await adapter.publish(_payload(caption=long_caption, hashtags=[]))

        assert result.success is True
        sent_text = client.post.call_args_list[1].kwargs["json"]["record"]["text"]
        assert len(sent_text) <= 300
