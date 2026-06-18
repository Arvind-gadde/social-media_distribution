"""OAuth services package."""

from .base import BaseOAuthService, OAuthError, TokenExpiredError, RateLimitError
from .facebook import FacebookOAuth
from .instagram import InstagramOAuth
from .linkedin import LinkedInOAuth
from .pinterest import PinterestOAuth
from .tiktok import TikTokOAuth
from .twitter import TwitterOAuth
from .youtube import YouTubeOAuth


OAUTH_SERVICES: dict[str, type[BaseOAuthService]] = {
    "instagram": InstagramOAuth,
    "twitter": TwitterOAuth,
    "youtube": YouTubeOAuth,
    "tiktok": TikTokOAuth,
    "linkedin": LinkedInOAuth,
    "facebook": FacebookOAuth,
    "pinterest": PinterestOAuth,
}


def get_oauth_service(platform: str) -> BaseOAuthService:
    """Factory: return an OAuth service instance for the given platform."""
    cls = OAUTH_SERVICES.get(platform)
    if cls is None:
        supported = ", ".join(sorted(OAUTH_SERVICES.keys()))
        raise ValueError(f"Unsupported OAuth platform: {platform}. Supported: {supported}")
    return cls()


__all__ = [
    "BaseOAuthService",
    "OAuthError",
    "TokenExpiredError",
    "RateLimitError",
    "InstagramOAuth",
    "YouTubeOAuth",
    "TikTokOAuth",
    "TwitterOAuth",
    "LinkedInOAuth",
    "FacebookOAuth",
    "PinterestOAuth",
    "OAUTH_SERVICES",
    "get_oauth_service",
]