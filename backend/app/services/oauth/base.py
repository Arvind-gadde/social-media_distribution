"""Base OAuth service class and common utilities."""
from __future__ import annotations

import asyncio
import base64
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import httpx

from app.core.logging import get_logger


def derive_pkce_challenge(code_verifier: str) -> str:
    """Return the S256 code_challenge for a given PKCE verifier."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

log = get_logger(__name__)


class OAuthError(Exception):
    """OAuth-related error."""
    pass


class TokenExpiredError(OAuthError):
    """OAuth token has expired."""
    pass


class RateLimitError(OAuthError):
    """API rate limit exceeded."""
    pass


class BaseOAuthService(ABC):
    """Base class for OAuth service implementations."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name."""
        pass
    
    @property
    @abstractmethod
    def platform_key(self) -> str:
        """Platform identifier key."""
        pass
    
    @property
    @abstractmethod
    def client_id(self) -> str:
        """OAuth client ID."""
        pass
    
    @property
    @abstractmethod
    def client_secret(self) -> str:
        """OAuth client secret."""
        pass
    
    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """OAuth authorization URL."""
        pass
    
    @property
    @abstractmethod
    def token_url(self) -> str:
        """OAuth token exchange URL."""
        pass
    
    @property
    @abstractmethod
    def required_scopes(self) -> list[str]:
        """Required OAuth scopes."""
        pass
    
    @property
    @abstractmethod
    def supports_publishing(self) -> bool:
        """Whether this platform supports content publishing."""
        pass
    
    @property
    @abstractmethod
    def supports_analytics(self) -> bool:
        """Whether this platform supports analytics fetching."""
        pass
    
    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: Optional[list[str]] = None,
        code_verifier: Optional[str] = None,
    ) -> str:
        """Generate OAuth authorization URL.

        When ``code_verifier`` is supplied the caller has opted in to PKCE; the
        corresponding S256 challenge is included automatically. Platform-specific
        hooks can read the verifier via :meth:`_get_auth_params` if they need to
        override behaviour.
        """
        scopes = scopes or self.required_scopes

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
        }

        if code_verifier:
            params["code_challenge"] = derive_pkce_challenge(code_verifier)
            params["code_challenge_method"] = "S256"

        # Add platform-specific parameters (may override PKCE defaults).
        params.update(self._get_auth_params(code_verifier=code_verifier))
        
        query_string = urlencode(params)
        return f"{self.authorization_url}?{query_string}"
    
    def _get_auth_params(self, code_verifier: Optional[str] = None) -> Dict[str, str]:
        """Get platform-specific authorization parameters."""
        return {}

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        # Add platform-specific data
        data.update(self._get_token_params())
        
        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Standardize response format
            return self._normalize_token_response(token_data)
            
        except httpx.HTTPStatusError as e:
            log.error("oauth.token_exchange.failed", 
                     platform=self.platform_key,
                     status_code=e.response.status_code,
                     response=e.response.text)
            raise OAuthError(f"Token exchange failed: {e.response.text}")
        except Exception as e:
            log.error("oauth.token_exchange.error", 
                     platform=self.platform_key,
                     error=str(e))
            raise OAuthError(f"Token exchange error: {str(e)}")
    
    def _get_token_params(self) -> Dict[str, str]:
        """Get platform-specific token exchange parameters."""
        return {}
    
    def _normalize_token_response(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize token response to standard format."""
        expires_in = token_data.get("expires_in")
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
            "scope": token_data.get("scope"),
            "token_type": token_data.get("token_type", "Bearer"),
        }
    
    @abstractmethod
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information."""
        pass
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self._supports_refresh():
            raise OAuthError("Platform does not support token refresh")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            return self._normalize_token_response(token_data)
            
        except httpx.HTTPStatusError as e:
            log.error("oauth.refresh.failed", 
                     platform=self.platform_key,
                     status_code=e.response.status_code,
                     response=e.response.text)
            raise OAuthError(f"Token refresh failed: {e.response.text}")
    
    def _supports_refresh(self) -> bool:
        """Whether this platform supports token refresh."""
        return True
    
    async def revoke_token(self, access_token: str) -> None:
        """Revoke access token."""
        # Default implementation - not all platforms support this
        log.info("oauth.revoke.not_supported", platform=self.platform_key)
    
    async def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid."""
        try:
            await self.get_user_profile(access_token)
            return True
        except Exception:
            return False
    
    async def _make_api_request(
        self, 
        method: str, 
        url: str, 
        access_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated API request."""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        
        try:
            response = await self.client.request(
                method, 
                url, 
                headers=headers, 
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            
            # Handle token expiration
            if response.status_code == 401:
                raise TokenExpiredError("Access token expired")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TokenExpiredError("Access token expired")
            elif e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After", "60")
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            else:
                raise OAuthError(f"API request failed: {e.response.text}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
