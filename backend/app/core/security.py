"""Security utilities — JWT, Fernet encryption, password hashing."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
import structlog
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.exceptions import AuthenticationError, ConfigurationError

settings = get_settings()
_logger = structlog.get_logger(__name__)

# ── Fernet encryption for platform tokens ────────────────────────────────

_fernet_instance: Fernet | None = None
_DEV_KEY_PATH = Path(os.environ.get("CF_DEV_FERNET_KEY_PATH", ".cache/fernet.key"))


def _load_or_create_dev_key() -> bytes:
    """Persist a generated Fernet key across dev restarts so already-encrypted
    tokens remain decryptable. Production must supply TOKEN_ENCRYPTION_KEY."""
    try:
        if _DEV_KEY_PATH.exists():
            return _DEV_KEY_PATH.read_bytes().strip()
        _DEV_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        new_key = Fernet.generate_key()
        _DEV_KEY_PATH.write_bytes(new_key)
        try:
            os.chmod(_DEV_KEY_PATH, 0o600)
        except OSError:
            pass  # Windows / non-POSIX filesystems
        _logger.warning(
            "dev_fernet_key_generated",
            path=str(_DEV_KEY_PATH),
            note="Set TOKEN_ENCRYPTION_KEY explicitly before deploying anywhere shared.",
        )
        return new_key
    except OSError as exc:
        _logger.warning("dev_fernet_key_persist_failed", error=str(exc))
        return Fernet.generate_key()


def _get_fernet() -> Fernet:
    """Cached Fernet instance for encrypting platform OAuth tokens."""
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.TOKEN_ENCRYPTION_KEY
        if not key:
            if settings.is_production:
                raise ConfigurationError(
                    "TOKEN_ENCRYPTION_KEY must be set in production. "
                    "Generate one with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`."
                )
            _fernet_instance = Fernet(_load_or_create_dev_key())
        else:
            _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


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
# Stateless, HMAC-signed state with a short expiry. Being stateless makes it
# multi-worker / multi-replica safe (no shared in-memory store that breaks when
# the callback lands on a different process), and the signature + exp bind the
# callback to a state THIS deployment issued — that binding is the CSRF defense.

_OAUTH_STATE_TTL_MINUTES = 10


def generate_oauth_state(provider: str) -> str:
    payload = {
        "provider": provider,
        "nonce": secrets.token_urlsafe(16),
        "type": "oauth_state",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_OAUTH_STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def consume_oauth_state(state: str, expected_provider: str) -> None:
    try:
        payload = jwt.decode(
            state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("OAuth state expired. Please retry login.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid OAuth state. Please retry login.")
    if payload.get("type") != "oauth_state" or payload.get("provider") != expected_provider:
        raise AuthenticationError("OAuth state provider mismatch.")
