"""Auth service — Google OAuth, user creation, token lifecycle."""

from __future__ import annotations

import structlog
import httpx

from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_token,
    encrypt_token,
)
from app.exceptions import AuthenticationError, ConflictError
from app.models.models import User
from app.repositories.repositories import UserRepository
from app.services.cache_service import CacheService

logger = structlog.get_logger(__name__)
settings = get_settings()

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class AuthService:
    """Business logic for authentication. No HTTP framework dependencies."""

    def __init__(self, user_repo: UserRepository, cache: CacheService) -> None:
        self._user_repo = user_repo
        self._cache = cache

    # ── Google OAuth ──────────────────────────────────────────────────────

    async def exchange_google_code(self, code: str) -> dict:
        """Exchange an authorization code for Google user info."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                token_resp = await client.post(
                    _GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                        "grant_type": "authorization_code",
                    },
                )
                token_resp.raise_for_status()
                tokens = token_resp.json()

                if "access_token" not in tokens:
                    raise AuthenticationError("Google did not return an access token")

                user_resp = await client.get(
                    _GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                user_resp.raise_for_status()
                return user_resp.json()

            except httpx.HTTPStatusError as exc:
                logger.error("google_token_exchange_failed", status=exc.response.status_code)
                raise AuthenticationError("Google authentication failed") from exc
            except httpx.RequestError as exc:
                logger.error("google_request_failed", error=str(exc))
                raise AuthenticationError("Could not reach Google services") from exc

    async def get_or_create_google_user(self, google_info: dict) -> User:
        """Find existing user by Google ID or email, or create a new one."""
        google_id = google_info.get("id", "")
        email = google_info.get("email", "")

        if not email:
            raise AuthenticationError("Google account did not provide an email address")

        # Try by Google ID first (most reliable)
        user = await self._user_repo.get_by_google_id(google_id)
        if not user:
            user = await self._user_repo.get_by_email(email)

        if user:
            # Refresh metadata
            user.google_id = google_id
            user.avatar_url = google_info.get("picture")
            user = await self._user_repo.save(user)
        else:
            user = User(
                email=email,
                name=google_info.get("name", email.split("@")[0]),
                avatar_url=google_info.get("picture"),
                google_id=google_id,
            )
            user = await self._user_repo.save(user)
            logger.info("user_created", user_id=str(user.id), email=email)

        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        """Create access and refresh tokens for a user."""
        return (
            create_access_token(str(user.id)),
            create_refresh_token(str(user.id)),
        )

    # ── Platform Token Management ─────────────────────────────────────────

    def store_platform_token(self, user: User, platform: str, token_data: dict) -> None:
        """Encrypt and store a platform OAuth token on the user record."""
        import json
        existing = user.encrypted_platform_tokens or {}
        encrypted_value = encrypt_token(json.dumps(token_data))
        existing[platform] = encrypted_value
        user.encrypted_platform_tokens = existing

        if platform not in (user.connected_platforms or []):
            user.connected_platforms = list(user.connected_platforms or []) + [platform]

    def get_platform_token(self, user: User, platform: str) -> dict | None:
        """Decrypt and return a platform token, or None if not connected."""
        import json
        encrypted = (user.encrypted_platform_tokens or {}).get(platform)
        if not encrypted:
            return None
        try:
            return json.loads(decrypt_token(encrypted))
        except Exception as exc:
            logger.warning("platform_token_decrypt_failed", platform=platform, error=str(exc))
            return None

    def remove_platform_token(self, user: User, platform: str) -> None:
        tokens = dict(user.encrypted_platform_tokens or {})
        tokens.pop(platform, None)
        user.encrypted_platform_tokens = tokens
        platforms = list(user.connected_platforms or [])
        if platform in platforms:
            platforms.remove(platform)
        user.connected_platforms = platforms
