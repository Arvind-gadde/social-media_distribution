"""Facebook OAuth 2.0 service implementation."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.core.logging import get_logger

from .base import BaseOAuthService, OAuthError

log = get_logger(__name__)


class FacebookOAuth(BaseOAuthService):
    """Facebook OAuth using Graph API v19.0."""

    GRAPH_VERSION = "v19.0"

    @property
    def platform_name(self) -> str:
        return "Facebook"

    @property
    def platform_key(self) -> str:
        return "facebook"

    @property
    def client_id(self) -> str:
        return os.getenv("FACEBOOK_CLIENT_ID", "")

    @property
    def client_secret(self) -> str:
        return os.getenv("FACEBOOK_CLIENT_SECRET", "")

    @property
    def authorization_url(self) -> str:
        return f"https://www.facebook.com/{self.GRAPH_VERSION}/dialog/oauth"

    @property
    def token_url(self) -> str:
        return f"https://graph.facebook.com/{self.GRAPH_VERSION}/oauth/access_token"

    @property
    def required_scopes(self) -> list[str]:
        return [
            "public_profile",
            "email",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
        ]

    @property
    def supports_publishing(self) -> bool:
        return True

    @property
    def supports_analytics(self) -> bool:
        return True

    def _supports_refresh(self) -> bool:
        # Facebook does not issue refresh tokens. Long-lived tokens are exchanged
        # via the fb_exchange_token grant on a separate code path.
        return False

    async def exchange_long_lived(self, short_lived_token: str) -> Dict[str, Any]:
        """Exchange a short-lived user token for a 60-day long-lived token."""
        try:
            response = await self.client.get(
                self.token_url,
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "fb_exchange_token": short_lived_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            expires_at = None
            if data.get("expires_in"):
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
            return {
                "access_token": data["access_token"],
                "refresh_token": None,
                "expires_at": expires_at,
                "scope": data.get("scope"),
                "token_type": data.get("token_type", "Bearer"),
            }
        except Exception as exc:
            log.error("facebook.long_lived.failed", error=str(exc))
            raise OAuthError(f"Facebook long-lived exchange failed: {exc}")

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        try:
            data = await self._make_api_request(
                "GET",
                f"https://graph.facebook.com/{self.GRAPH_VERSION}/me",
                access_token,
                params={"fields": "id,name,email,picture.type(large)"},
            )
            picture = (data.get("picture") or {}).get("data", {}).get("url")
            return {
                "id": data.get("id"),
                "username": data.get("email"),
                "display_name": data.get("name"),
                "avatar_url": picture,
                "profile_url": f"https://facebook.com/{data.get('id')}",
                "email": data.get("email"),
            }
        except Exception as exc:
            log.error("facebook.profile.failed", error=str(exc))
            raise OAuthError(f"Failed to get Facebook profile: {exc}")

    async def list_pages(self, access_token: str) -> list[Dict[str, Any]]:
        """Return Pages the user manages with their per-page access tokens."""
        try:
            data = await self._make_api_request(
                "GET",
                f"https://graph.facebook.com/{self.GRAPH_VERSION}/me/accounts",
                access_token,
                params={"fields": "id,name,access_token,category,tasks"},
            )
            return [
                {
                    "page_id": item.get("id"),
                    "name": item.get("name"),
                    "access_token": item.get("access_token"),
                    "category": item.get("category"),
                    "tasks": item.get("tasks", []),
                }
                for item in data.get("data", [])
            ]
        except Exception as exc:
            log.error("facebook.pages.failed", error=str(exc))
            raise OAuthError(f"Failed to list Facebook pages: {exc}")
