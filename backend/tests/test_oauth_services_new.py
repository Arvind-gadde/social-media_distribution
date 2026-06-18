"""Tests for the LinkedIn / Facebook / Pinterest OAuth services."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.oauth import (
    FacebookOAuth,
    LinkedInOAuth,
    OAUTH_SERVICES,
    PinterestOAuth,
    get_oauth_service,
)


def _mock_response(status_code: int = 200, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = ""
    resp.raise_for_status = MagicMock()
    return resp


# ─── Factory ──────────────────────────────────────────────────────────────


def test_factory_returns_concrete_service():
    assert isinstance(get_oauth_service("linkedin"), LinkedInOAuth)
    assert isinstance(get_oauth_service("facebook"), FacebookOAuth)
    assert isinstance(get_oauth_service("pinterest"), PinterestOAuth)


def test_factory_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported OAuth platform"):
        get_oauth_service("snapchat")


def test_oauth_services_registry_covers_seven_platforms():
    assert set(OAUTH_SERVICES.keys()) == {
        "instagram", "twitter", "youtube", "tiktok",
        "linkedin", "facebook", "pinterest",
    }


# ─── LinkedIn ─────────────────────────────────────────────────────────────


class TestLinkedInOAuth:
    def test_metadata(self):
        svc = LinkedInOAuth()
        assert svc.platform_key == "linkedin"
        assert svc.supports_publishing is True
        assert "w_member_social" in svc.required_scopes
        assert svc.authorization_url.startswith("https://www.linkedin.com/oauth")

    @pytest.mark.asyncio
    async def test_get_user_profile_normalizes_userinfo(self):
        svc = LinkedInOAuth()
        with patch.object(svc, "_make_api_request", new=AsyncMock(return_value={
            "sub": "abc123",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "picture": "https://cdn.example/a.png",
            "locale": "en_US",
        })):
            profile = await svc.get_user_profile("token")
        assert profile["id"] == "abc123"
        assert profile["author_urn"] == "urn:li:person:abc123"
        assert profile["email"] == "ada@example.com"


# ─── Facebook ─────────────────────────────────────────────────────────────


class TestFacebookOAuth:
    def test_metadata(self):
        svc = FacebookOAuth()
        assert svc.platform_key == "facebook"
        assert "pages_manage_posts" in svc.required_scopes
        assert svc.token_url.endswith("/oauth/access_token")

    def test_no_native_refresh_support(self):
        assert FacebookOAuth()._supports_refresh() is False

    @pytest.mark.asyncio
    async def test_exchange_long_lived_token(self):
        svc = FacebookOAuth()
        svc.client = MagicMock()
        svc.client.get = AsyncMock(return_value=_mock_response(200, {
            "access_token": "long-lived",
            "expires_in": 5184000,
            "token_type": "bearer",
        }))
        result = await svc.exchange_long_lived("short-lived")
        assert result["access_token"] == "long-lived"
        assert result["expires_at"] is not None
        assert result["refresh_token"] is None

    @pytest.mark.asyncio
    async def test_list_pages_returns_page_tokens(self):
        svc = FacebookOAuth()
        with patch.object(svc, "_make_api_request", new=AsyncMock(return_value={
            "data": [
                {"id": "p1", "name": "Page One", "access_token": "tok1", "category": "Brand", "tasks": ["CREATE_CONTENT"]},
                {"id": "p2", "name": "Page Two", "access_token": "tok2", "category": "Blog", "tasks": []},
            ]
        })):
            pages = await svc.list_pages("user_tok")
        assert len(pages) == 2
        assert pages[0]["access_token"] == "tok1"
        assert pages[0]["page_id"] == "p1"


# ─── Pinterest ────────────────────────────────────────────────────────────


class TestPinterestOAuth:
    def test_metadata(self):
        svc = PinterestOAuth()
        assert svc.platform_key == "pinterest"
        assert "pins:write" in svc.required_scopes
        assert svc.token_url == "https://api.pinterest.com/v5/oauth/token"

    @pytest.mark.asyncio
    async def test_exchange_uses_basic_auth(self):
        svc = PinterestOAuth()
        svc.client = MagicMock()
        svc.client.post = AsyncMock(return_value=_mock_response(200, {
            "access_token": "at", "refresh_token": "rt", "expires_in": 3600, "token_type": "bearer",
        }))
        result = await svc.exchange_code_for_tokens("code", "https://app/cb")
        assert result["access_token"] == "at"
        assert result["refresh_token"] == "rt"
        headers = svc.client.post.call_args.kwargs["headers"]
        assert headers["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    async def test_list_boards(self):
        svc = PinterestOAuth()
        with patch.object(svc, "_make_api_request", new=AsyncMock(return_value={
            "items": [
                {"id": "b1", "name": "Board One", "privacy": "PUBLIC", "pin_count": 5},
            ]
        })):
            boards = await svc.list_boards("token")
        assert boards[0]["id"] == "b1"
        assert boards[0]["pin_count"] == 5
