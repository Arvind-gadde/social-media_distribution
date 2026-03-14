"""Security utilities — JWT, Fernet encryption, password hashing."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.exceptions import AuthenticationError

settings = get_settings()

# ── Fernet encryption for platform tokens ────────────────────────────────

def _get_fernet() -> Fernet:
    """Lazily initialise Fernet with the app key."""
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        # Dev fallback — generate a temporary key (tokens won't survive restart)
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a platform OAuth token for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored platform OAuth token."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise AuthenticationError("Platform token could not be decrypted") from exc


# ── JWT ───────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access", "jti": secrets.token_hex(16)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh", "jti": secrets.token_hex(16)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT. Raises AuthenticationError on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(f"Invalid token: {exc}")

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Expected {expected_type} token, got {payload.get('type')}")

    return payload


# ── OAuth state CSRF protection ───────────────────────────────────────────

_PENDING_OAUTH_STATES: dict[str, str] = {}
_MAX_STATES = 500


def generate_oauth_state(provider: str) -> str:
    state = secrets.token_urlsafe(32)
    if len(_PENDING_OAUTH_STATES) >= _MAX_STATES:
        # Evict oldest half
        for key in list(_PENDING_OAUTH_STATES)[:_MAX_STATES // 2]:
            del _PENDING_OAUTH_STATES[key]
    _PENDING_OAUTH_STATES[state] = provider
    return state


def consume_oauth_state(state: str, expected_provider: str) -> None:
    provider = _PENDING_OAUTH_STATES.pop(state, None)
    if provider is None:
        raise AuthenticationError("Invalid or expired OAuth state. Please retry login.")
    if provider != expected_provider:
        raise AuthenticationError("OAuth state provider mismatch.")
