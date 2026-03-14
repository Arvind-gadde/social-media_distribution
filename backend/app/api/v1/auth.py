"""Auth routes — Google OAuth with HttpOnly cookie tokens."""
from __future__ import annotations
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from app.api.deps import AuthSvc, CurrentUser, Cache
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, generate_oauth_state, consume_oauth_state,
)
from app.exceptions import AuthenticationError
from app.schemas.schemas import AuthResponse, UserResponse
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_ACCESS_COOKIE = "cf_access_token"
_REFRESH_COOKIE = "cf_refresh_token"
_SECURE = settings.is_production


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(_ACCESS_COOKIE, access, httponly=True, secure=_SECURE,
        samesite="lax", max_age=settings.JWT_ACCESS_EXPIRE_MINUTES * 60, path="/")
    response.set_cookie(_REFRESH_COOKIE, refresh, httponly=True, secure=_SECURE,
        samesite="lax", max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 86400, path="/api/v1/auth")


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_ACCESS_COOKIE, path="/")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/google/url")
async def google_auth_url() -> dict:
    state = generate_oauth_state("google")
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code&scope=openid email profile&access_type=offline"
        f"&state={state}"
    )
    return {"url": url, "state": state}


@router.get("/google/callback")
async def google_callback(code: str, state: str, auth_service: AuthSvc) -> Response:
    consume_oauth_state(state, "google")
    google_info = await auth_service.exchange_google_code(code)
    user = await auth_service.get_or_create_google_user(google_info)
    access, refresh = auth_service.issue_tokens(user)
    resp = JSONResponse(
        content={"user": UserResponse.model_validate(user).model_dump(mode="json")}
    )
    _set_auth_cookies(resp, access, refresh)
    return resp


@router.post("/refresh")
async def refresh_token(request: Request, auth_service: AuthSvc) -> Response:
    raw = request.cookies.get(_REFRESH_COOKIE)
    if not raw:
        raise AuthenticationError("No refresh token")
    payload = decode_token(raw, expected_type="refresh")
    user_id = payload.get("sub")
    from app.repositories.repositories import UserRepository
    from app.db.session import AsyncSessionLocal
    import uuid
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise AuthenticationError("User not found")
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    resp = JSONResponse(content={"ok": True})
    _set_auth_cookies(resp, access, refresh)
    return resp


@router.post("/logout")
async def logout(request: Request, current_user: CurrentUser, cache: Cache) -> Response:
    raw_access = request.cookies.get(_ACCESS_COOKIE)
    if raw_access:
        try:
            payload = decode_token(raw_access)
            jti = payload.get("jti")
            if jti:
                await cache.blacklist_jti(jti, settings.JWT_ACCESS_EXPIRE_MINUTES * 60)
        except Exception:
            pass
    resp = Response(status_code=204)
    _clear_auth_cookies(resp)
    return resp


@router.get("/me", response_model=AuthResponse)
async def get_me(current_user: CurrentUser) -> AuthResponse:
    return AuthResponse(user=UserResponse.model_validate(current_user))
