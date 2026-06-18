"""Pinterest OAuth 2.0 service implementation."""
from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.core.logging import get_logger

from .base import BaseOAuthService, OAuthError

log = get_logger(__name__)


class PinterestOAuth(BaseOAuthService):
    """Pinterest OAuth 2.0 using API v5."""

    API_BASE = "https://api.pinterest.com/v5"

    @property
    def platform_name(self) -> str:
        return "Pinterest"

    @property
    def platform_key(self) -> str:
        return "pinterest"

    @property
    def client_id(self) -> str:
        return os.getenv("PINTEREST_CLIENT_ID", "")

    @property
    def client_secret(self) -> str:
        return os.getenv("PINTEREST_CLIENT_SECRET", "")

    @property
    def authorization_url(self) -> str:
        return "https://www.pinterest.com/oauth/"

    @property
    def token_url(self) -> str:
        return "https://api.pinterest.com/v5/oauth/token"

    @property
    def required_scopes(self) -> list[str]:
        return [
            "user_accounts:read",
            "boards:read",
            "pins:read",
            "pins:write",
        ]

    @property
    def supports_publishing(self) -> bool:
        return True

    @property
    def supports_analytics(self) -> bool:
        return True

    def _basic_auth_header(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> Dict[str, Any]:
        """Pinterest requires HTTP Basic auth for the token request."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={**self._basic_auth_header(), "Accept": "application/json"},
            )
            response.raise_for_status()
            return self._normalize_token_response(response.json())
        except Exception as exc:
            log.error("pinterest.token_exchange.failed", error=str(exc))
            raise OAuthError(f"Pinterest token exchange failed: {exc}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            response = await self.client.post(
                self.token_url,
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                headers={**self._basic_auth_header(), "Accept": "application/json"},
            )
            response.raise_for_status()
            return self._normalize_token_response(response.json())
        except Exception as exc:
            log.error("pinterest.refresh.failed", error=str(exc))
            raise OAuthError(f"Pinterest refresh failed: {exc}")

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        try:
            data = await self._make_api_request(
                "GET", f"{self.API_BASE}/user_account", access_token
            )
            return {
                "id": data.get("username") or data.get("id"),
                "username": data.get("username"),
                "display_name": data.get("business_name") or data.get("username"),
                "avatar_url": data.get("profile_image"),
                "profile_url": f"https://www.pinterest.com/{data.get('username','')}/",
                "followers_count": data.get("follower_count", 0),
                "following_count": data.get("following_count", 0),
                "posts_count": data.get("pin_count", 0),
                "account_type": data.get("account_type"),
            }
        except Exception as exc:
            log.error("pinterest.profile.failed", error=str(exc))
            raise OAuthError(f"Failed to get Pinterest profile: {exc}")

    async def list_boards(self, access_token: str) -> list[Dict[str, Any]]:
        try:
            data = await self._make_api_request(
                "GET", f"{self.API_BASE}/boards", access_token, params={"page_size": 100}
            )
            return [
                {
                    "id": b.get("id"),
                    "name": b.get("name"),
                    "privacy": b.get("privacy"),
                    "pin_count": b.get("pin_count", 0),
                }
                for b in data.get("items", [])
            ]
        except Exception as exc:
            log.error("pinterest.boards.failed", error=str(exc))
            raise OAuthError(f"Failed to list Pinterest boards: {exc}")
