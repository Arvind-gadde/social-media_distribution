"""
DEV BYPASS — auto-auth middleware for local development.

When APP_ENV=development and DEV_BYPASS_AUTH=true in your .env,
every request is automatically authenticated as a hardcoded dev user.
No login needed. No cookies. No tokens.

TO ENABLE:  add  DEV_BYPASS_AUTH=true  to backend/.env
TO DISABLE: remove it or set DEV_BYPASS_AUTH=false
NEVER deploy with this enabled — it bypasses ALL authentication.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

_DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class DevAuthBypassMiddleware(BaseHTTPMiddleware):
    """
    Injects a fake User object into request.state.dev_user.
    The overridden get_current_user dependency (in deps.py) picks this up
    and returns it directly, skipping all JWT/cookie validation.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.is_production and getattr(settings, "DEV_BYPASS_AUTH", False):
            # Lazy import to avoid circular imports at module load time
            from app.models.models import User

            dev_user = User()
            dev_user.id                       = _DEV_USER_ID
            dev_user.email                    = "dev@local.dev"
            dev_user.name                     = "Dev User"
            dev_user.avatar_url               = None
            dev_user.google_id                = None
            dev_user.password_hash            = None
            dev_user.is_active                = True
            dev_user.connected_platforms      = []
            dev_user.encrypted_platform_tokens = {}
            dev_user.created_at               = datetime.now(timezone.utc)
            dev_user.updated_at               = datetime.now(timezone.utc)

            request.state.dev_user = dev_user

        return await call_next(request)