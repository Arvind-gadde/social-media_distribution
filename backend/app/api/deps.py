"""FastAPI dependency factories — DI wiring for all routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.exceptions import AuthenticationError
from app.models.models import User
from app.repositories.repositories import UserRepository, PostRepository
from app.services.auth_service import AuthService
from app.services.ai_service import AIService
from app.services.media_service import MediaService
from app.services.cache_service import CacheService
from app.services.post_service import PostService
from app.config import get_settings

_security = HTTPBearer(auto_error=False)


async def get_cache() -> CacheService:
    return CacheService()


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    cf_access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    elif cf_access_token:
        token = cf_access_token

    if not token:
        raise AuthenticationError("Authentication required")

    payload = decode_token(token, expected_type="access")
    jti = payload.get("jti", "")
    if jti and await cache.is_jti_blacklisted(jti):
        raise AuthenticationError("Token has been revoked")

    user_id = payload.get("sub")
    repo = UserRepository(db)
    user = await repo.get_by_id(__import__("uuid").UUID(user_id))
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
) -> AuthService:
    return AuthService(UserRepository(db), cache)


async def get_ai_service() -> AIService:
    settings = get_settings()
    return AIService(
        gemini_api_key=settings.GEMINI_API_KEY or None,
        openai_api_key=settings.OPENAI_API_KEY or None,
    )


async def get_post_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostService:
    settings = get_settings()
    ai = AIService(
        gemini_api_key=settings.GEMINI_API_KEY or None,
        openai_api_key=settings.OPENAI_API_KEY or None,
    )
    return PostService(PostRepository(db), ai)


async def get_media_service() -> MediaService:
    return MediaService()


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
PostSvc = Annotated[PostService, Depends(get_post_service)]
AISvc = Annotated[AIService, Depends(get_ai_service)]
MediaSvc = Annotated[MediaService, Depends(get_media_service)]
Cache = Annotated[CacheService, Depends(get_cache)]