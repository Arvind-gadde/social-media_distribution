"""LinkedIn OAuth 2.0 service implementation."""
from __future__ import annotations

import os
from typing import Any, Dict

from app.core.logging import get_logger

from .base import BaseOAuthService, OAuthError

log = get_logger(__name__)


class LinkedInOAuth(BaseOAuthService):
    """LinkedIn OAuth 2.0 service using Sign In with LinkedIn v2."""

    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    @property
    def platform_key(self) -> str:
        return "linkedin"

    @property
    def client_id(self) -> str:
        return os.getenv("LINKEDIN_CLIENT_ID", "")

    @property
    def client_secret(self) -> str:
        return os.getenv("LINKEDIN_CLIENT_SECRET", "")

    @property
    def authorization_url(self) -> str:
        return "https://www.linkedin.com/oauth/v2/authorization"

    @property
    def token_url(self) -> str:
        return "https://www.linkedin.com/oauth/v2/accessToken"

    @property
    def required_scopes(self) -> list[str]:
        return ["openid", "profile", "email", "w_member_social"]

    @property
    def supports_publishing(self) -> bool:
        return True

    @property
    def supports_analytics(self) -> bool:
        return True

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        try:
            data = await self._make_api_request(
                "GET",
                "https://api.linkedin.com/v2/userinfo",
                access_token,
            )
            return {
                "id": data.get("sub"),
                "username": data.get("email"),
                "display_name": data.get("name") or data.get("given_name", ""),
                "avatar_url": data.get("picture"),
                "profile_url": f"https://www.linkedin.com/in/{data.get('sub', '')}",
                "email": data.get("email"),
                "locale": data.get("locale"),
                "author_urn": f"urn:li:person:{data.get('sub')}" if data.get("sub") else None,
            }
        except Exception as exc:
            log.error("linkedin.profile.failed", error=str(exc))
            raise OAuthError(f"Failed to get LinkedIn profile: {exc}")

    def _supports_refresh(self) -> bool:
        # LinkedIn refresh tokens require additional product approval.
        return True
