"""Instagram OAuth service implementation."""
from __future__ import annotations

import os
from typing import Dict, Any

from .base import BaseOAuthService, OAuthError
from app.core.logging import get_logger

log = get_logger(__name__)


class InstagramOAuth(BaseOAuthService):
    """Instagram OAuth service using Instagram Basic Display API."""
    
    @property
    def platform_name(self) -> str:
        return "Instagram"
    
    @property
    def platform_key(self) -> str:
        return "instagram"
    
    @property
    def client_id(self) -> str:
        return os.getenv("INSTAGRAM_CLIENT_ID", "")
    
    @property
    def client_secret(self) -> str:
        return os.getenv("INSTAGRAM_CLIENT_SECRET", "")
    
    @property
    def authorization_url(self) -> str:
        return "https://api.instagram.com/oauth/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://api.instagram.com/oauth/access_token"
    
    @property
    def required_scopes(self) -> list[str]:
        return ["user_profile", "user_media"]
    
    @property
    def supports_publishing(self) -> bool:
        # Instagram Basic Display API doesn't support publishing
        # Would need Instagram Graph API for business accounts
        return False
    
    @property
    def supports_analytics(self) -> bool:
        return True
    
    def _get_auth_params(self, code_verifier: str | None = None) -> Dict[str, str]:
        """Instagram-specific authorization parameters."""
        return {
            "response_type": "code",
        }
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get Instagram user profile."""
        try:
            # Get user info
            user_data = await self._make_api_request(
                "GET",
                "https://graph.instagram.com/me",
                access_token,
                params={
                    "fields": "id,username,account_type,media_count"
                }
            )
            
            return {
                "id": user_data["id"],
                "username": user_data.get("username"),
                "display_name": user_data.get("username"),  # Instagram doesn't have separate display name
                "avatar_url": None,  # Not available in Basic Display API
                "profile_url": f"https://instagram.com/{user_data.get('username', '')}" if user_data.get("username") else None,
                "followers_count": 0,  # Not available in Basic Display API
                "following_count": 0,  # Not available in Basic Display API
                "posts_count": user_data.get("media_count", 0),
                "account_type": user_data.get("account_type", "PERSONAL"),
            }
            
        except Exception as e:
            log.error("instagram.profile.failed", error=str(e))
            raise OAuthError(f"Failed to get Instagram profile: {str(e)}")
    
    async def get_user_media(self, access_token: str, limit: int = 25) -> list[Dict[str, Any]]:
        """Get user's Instagram media."""
        try:
            media_data = await self._make_api_request(
                "GET",
                "https://graph.instagram.com/me/media",
                access_token,
                params={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
                    "limit": limit
                }
            )
            
            return media_data.get("data", [])
            
        except Exception as e:
            log.error("instagram.media.failed", error=str(e))
            raise OAuthError(f"Failed to get Instagram media: {str(e)}")
    
    async def get_media_insights(self, access_token: str, media_id: str) -> Dict[str, Any]:
        """Get insights for a specific media item."""
        try:
            # Note: Insights require Instagram Graph API and business account
            # This is a placeholder for Basic Display API
            return {
                "impressions": 0,
                "reach": 0,
                "likes": 0,
                "comments": 0,
                "saves": 0,
                "shares": 0,
            }
            
        except Exception as e:
            log.error("instagram.insights.failed", media_id=media_id, error=str(e))
            raise OAuthError(f"Failed to get Instagram insights: {str(e)}")
    
    def _supports_refresh(self) -> bool:
        """Instagram Basic Display API supports token refresh."""
        return True
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Instagram access token."""
        # Instagram uses a different endpoint for token refresh
        try:
            response = await self.client.get(
                "https://graph.instagram.com/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": refresh_token,  # Instagram uses access_token instead of refresh_token
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            return self._normalize_token_response(token_data)
            
        except Exception as e:
            log.error("instagram.refresh.failed", error=str(e))
            raise OAuthError(f"Instagram token refresh failed: {str(e)}")
    
    async def exchange_short_token_for_long(self, short_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived token."""
        try:
            response = await self.client.get(
                "https://graph.instagram.com/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": self.client_secret,
                    "access_token": short_token,
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            return self._normalize_token_response(token_data)
            
        except Exception as e:
            log.error("instagram.exchange_token.failed", error=str(e))
            raise OAuthError(f"Instagram token exchange failed: {str(e)}")
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for Instagram tokens."""
        # Instagram requires form data instead of JSON
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        
        try:
            # First, get short-lived token
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            
            short_token_data = response.json()
            short_token = short_token_data["access_token"]
            
            # Exchange for long-lived token
            long_token_data = await self.exchange_short_token_for_long(short_token)
            
            return long_token_data
            
        except Exception as e:
            log.error("instagram.code_exchange.failed", error=str(e))
            raise OAuthError(f"Instagram code exchange failed: {str(e)}")