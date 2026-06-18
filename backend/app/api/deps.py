"""FastAPI dependency factories — DI wiring for all routes.

Key workspace-aware dependencies:
  - CurrentUser: authenticated user
  - CurrentWorkspace: resolved workspace from header/path
  - WorkspaceContext: RunContext for background tasks
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Path, Request, Cookie, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.exceptions import AuthenticationError
from app.models.models import User
from app.repositories.repositories import (
    UserRepository, WorkspaceRepository, NicheRepository,
    ContentProjectRepository, GoalRepository,
    SourceDocumentRepository, WorkspaceInsightRepository,
)
from app.services.auth_service import AuthService
from app.services.ai_service import AIService
from app.services.media_service import MediaService
from app.services.cache_service import CacheService
from app.config import get_settings
from app.runtime.context import RunContext

_security = HTTPBearer(auto_error=False)
_cache_singleton: CacheService | None = None


async def get_cache() -> CacheService:
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = CacheService()
    return _cache_singleton


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    cf_access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    settings = get_settings()

    # DEV BYPASS
    if not settings.is_production and getattr(settings, "DEV_BYPASS_AUTH", False):
        dev_user = getattr(request.state, "dev_user", None)
        if dev_user is not None:
            return dev_user

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
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


async def resolve_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    x_workspace_id: Annotated[str | None, Header()] = None,
):
    """Resolve the active workspace for the current request.

    Resolution order:
      1. X-Workspace-Id header (explicit)
      2. First workspace where user has active membership (default)

    Returns the Workspace ORM object. Raises 403 if user has no access.
    """
    from app.domains.control.models import (
        Workspace, WorkspaceMembership, InviteStatus,
    )
    from sqlalchemy import select

    repo = WorkspaceRepository(db)

    if x_workspace_id:
        try:
            workspace_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace ID")

        workspace = await repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Verify membership
        result = await db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.invite_status == InviteStatus.ACTIVE,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a member of this workspace")

        return workspace

    # Default: first workspace
    workspaces = await repo.list_for_user(user.id)
    if not workspaces:
        raise HTTPException(
            status_code=404,
            detail="No workspace found. Complete onboarding first.",
        )
    return workspaces[0]


def get_run_context(
    user: Annotated[User, Depends(get_current_user)],
    workspace=Depends(resolve_workspace),
) -> RunContext:
    """Create a RunContext for the current request."""
    return RunContext(
        workspace_id=workspace.id,
        actor_id=str(user.id),
        trigger="manual",
    )


# ── Service factories ─────────────────────────────────────────────────────


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


async def get_llm_provider():
    """Create workspace-aware LLM provider from app settings."""
    from app.integrations.llm.provider import create_llm_provider
    settings = get_settings()
    return create_llm_provider(
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GEMINI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
    )


async def get_media_service() -> MediaService:
    return MediaService()


# ── Type aliases ──────────────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentWorkspace = Annotated[object, Depends(resolve_workspace)]
WorkspaceCtx = Annotated[RunContext, Depends(get_run_context)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
AISvc = Annotated[AIService, Depends(get_ai_service)]
MediaSvc = Annotated[MediaService, Depends(get_media_service)]
Cache = Annotated[CacheService, Depends(get_cache)]