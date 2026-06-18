"""Unit tests for platform webhook HMAC signature validation."""
from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from app.api.v1 import platform_webhooks


@pytest.fixture
def patch_settings(monkeypatch):
    settings = platform_webhooks.get_settings()
    overrides = {
        "INSTAGRAM_APP_SECRET": "ig-secret",
        "YOUTUBE_WEBHOOK_CHANNEL_TOKEN": "yt-token",
        "TWITTER_API_SECRET": "tw-secret",
        "LINKEDIN_WEBHOOK_SECRET": "li-secret",
        "LINKEDIN_CLIENT_SECRET": "li-secret",
        "TIKTOK_WEBHOOK_SECRET": "tt-secret",
    }
    for key, value in overrides.items():
        monkeypatch.setattr(settings, key, value, raising=False)
    return settings


@pytest.mark.asyncio
async def test_instagram_valid_hmac_accepted(patch_settings):
    body = b'{"entry":[{"id":"abc"}]}'
    digest = hmac.new(b"ig-secret", body, hashlib.sha256).hexdigest()
    assert await platform_webhooks._validate_signature(
        "instagram", body, f"sha256={digest}"
    ) is True


@pytest.mark.asyncio
async def test_instagram_wrong_secret_rejected(patch_settings):
    body = b'{"x":1}'
    bogus = hmac.new(b"wrong", body, hashlib.sha256).hexdigest()
    assert await platform_webhooks._validate_signature(
        "instagram", body, f"sha256={bogus}"
    ) is False


@pytest.mark.asyncio
async def test_instagram_missing_secret_rejects(monkeypatch):
    settings = platform_webhooks.get_settings()
    monkeypatch.setattr(settings, "INSTAGRAM_APP_SECRET", "", raising=False)
    assert await platform_webhooks._validate_signature(
        "instagram", b"{}", "sha256=anything"
    ) is False


@pytest.mark.asyncio
async def test_youtube_channel_token_match(patch_settings):
    assert await platform_webhooks._validate_signature(
        "youtube", b"any", "yt-token"
    ) is True
    assert await platform_webhooks._validate_signature(
        "youtube", b"any", "bad-token"
    ) is False


@pytest.mark.asyncio
async def test_twitter_base64_hmac_accepted(patch_settings):
    body = b'{"tweet":1}'
    digest = hmac.new(b"tw-secret", body, hashlib.sha256).digest()
    b64 = base64.b64encode(digest).decode("ascii")
    assert await platform_webhooks._validate_signature(
        "twitter", body, f"sha256={b64}"
    ) is True
    assert await platform_webhooks._validate_signature(
        "twitter", body, "sha256=garbage"
    ) is False


@pytest.mark.asyncio
async def test_linkedin_hex_or_base64_accepted(patch_settings):
    body = b'{"event":"x"}'
    digest = hmac.new(b"li-secret", body, hashlib.sha256)
    hex_sig = digest.hexdigest()
    b64_sig = base64.b64encode(digest.digest()).decode("ascii")
    assert await platform_webhooks._validate_signature("linkedin", body, hex_sig) is True
    assert await platform_webhooks._validate_signature("linkedin", body, b64_sig) is True
    assert await platform_webhooks._validate_signature("linkedin", body, "deadbeef") is False


@pytest.mark.asyncio
async def test_tiktok_timestamp_payload_signed(patch_settings):
    body = b'{"event_id":"e1"}'
    ts = "1700000000"
    signed = ts.encode() + b"." + body
    digest = hmac.new(b"tt-secret", signed, hashlib.sha256).hexdigest()
    assert await platform_webhooks._validate_signature(
        "tiktok", body, f"t={ts},s={digest}"
    ) is True
    # Wrong timestamp invalidates the HMAC.
    assert await platform_webhooks._validate_signature(
        "tiktok", body, f"t=999,s={digest}"
    ) is False
    # Missing pieces.
    assert await platform_webhooks._validate_signature(
        "tiktok", body, f"t={ts}"
    ) is False


@pytest.mark.asyncio
async def test_unknown_platform_returns_false(patch_settings):
    assert await platform_webhooks._validate_signature(
        "myspace", b"{}", "sha256=anything"
    ) is False


@pytest.mark.asyncio
async def test_missing_signature_returns_false():
    assert await platform_webhooks._validate_signature("instagram", b"{}", None) is False
