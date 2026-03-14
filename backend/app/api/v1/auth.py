"""Auth routes — Google OAuth + email/password with HttpOnly cookie tokens."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import AuthSvc, CurrentUser, Cache
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, generate_oauth_state, consume_oauth_state,
)
from app.exceptions import AuthenticationError
from app.schemas.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_ACCESS_COOKIE = "cf_access_token"
_REFRESH_COOKIE = "cf_refresh_token"
_SECURE = settings.is_production


def _set_auth_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    response.set_cookie(
        _ACCESS_COOKIE, access, httponly=True, secure=_SECURE,
        samesite="lax", max_age=settings.JWT_ACCESS_EXPIRE_MINUTES * 60, path="/",
    )
    if refresh:
        response.set_cookie(
            _REFRESH_COOKIE, refresh, httponly=True, secure=_SECURE,
            samesite="lax", max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 86400,
            path="/api/v1/auth",
        )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_ACCESS_COOKIE, path="/")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")


def _user_json(user) -> dict:
    return UserResponse.model_validate(user).model_dump(mode="json")


def _auth_response(user, access: str, refresh: str, status_code: int = 200) -> Response:
    """
    Build auth response.
    - access_token is returned in the JSON body so the frontend can store
      it in memory and send as Bearer header (fixes Vite proxy cookie issues).
    - Cookies are also set as a fallback for page refreshes.
    """
    resp = JSONResponse(
        content={
            "user": _user_json(user),
            "access_token": access,
        },
        status_code=status_code,
    )
    _set_auth_cookies(resp, access, refresh)
    return resp


# ── Email / Password ──────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, auth_service: AuthSvc) -> Response:
    user = await auth_service.register(
        email=body.email,
        password=body.password,
        name=body.name,
    )
    access, refresh = auth_service.issue_tokens(user)
    return _auth_response(user, access, refresh, status_code=201)


@router.post("/login")
async def login(body: LoginRequest, auth_service: AuthSvc) -> Response:
    user = await auth_service.login(email=body.email, password=body.password)
    access, refresh = auth_service.issue_tokens(user)
    return _auth_response(user, access, refresh)


# ── Google OAuth ──────────────────────────────────────────────────────────

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
    return _auth_response(user, access, refresh)


# ── Token management ──────────────────────────────────────────────────────

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
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    resp = JSONResponse(content={"ok": True, "access_token": access})
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


@router.get("/me")
async def get_me(response: Response, current_user: CurrentUser) -> Response:
    access_token = create_access_token(str(current_user.id))
    _set_auth_cookies(response, access_token, None)
    
    return JSONResponse(
        content={
            "user": _user_json(current_user),
            "access_token": access_token,
        },
    )