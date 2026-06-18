"""MFA / TOTP enrollment + verification.

The TOTP implementation follows RFC 6238 (SHA-1, 30s step, 6 digits) so it is
compatible with Google Authenticator, 1Password, Authy, etc.

The module deliberately avoids the ``pyotp`` dep — the TOTP/HOTP algorithm is
short enough to vendor and keeps test runs hermetic.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from urllib.parse import quote

# RFC 4648 base32 alphabet (uppercase, no padding).
_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _b32_no_pad(value: bytes) -> str:
    """Base32-encode without trailing '=' padding."""
    return base64.b32encode(value).decode("ascii").rstrip("=")


def _b32_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 8)
    return base64.b32decode(value.upper() + pad, casefold=True)


def generate_secret(num_bytes: int = 20) -> str:
    """Generate a fresh base32-encoded TOTP secret (160 bits by default)."""
    return _b32_no_pad(secrets.token_bytes(num_bytes))


def generate_backup_codes(count: int = 10, *, group_size: int = 4) -> list[str]:
    """Return human-readable single-use backup codes (8 chars, dash-grouped)."""
    codes: list[str] = []
    for _ in range(count):
        raw = secrets.token_hex(4).upper()  # 8 hex chars
        codes.append(f"{raw[:group_size]}-{raw[group_size:]}")
    return codes


def _hotp(secret: bytes, counter: int, digits: int = 6) -> str:
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    return str(code_int % (10**digits)).zfill(digits)


def generate_totp(secret_b32: str, *, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    """Compute the current 6-digit TOTP for the given base32 secret."""
    secret = _b32_decode(secret_b32)
    counter = int((for_time if for_time is not None else time.time()) // step)
    return _hotp(secret, counter, digits=digits)


def verify_totp(
    secret_b32: str,
    code: str,
    *,
    for_time: int | None = None,
    step: int = 30,
    digits: int = 6,
    window: int = 1,
) -> bool:
    """Verify a 6-digit code; allow ±``window`` steps to tolerate clock drift."""
    if not secret_b32 or not code or len(code) != digits or not code.isdigit():
        return False
    secret = _b32_decode(secret_b32)
    now = int(for_time if for_time is not None else time.time())
    counter = now // step
    for offset in range(-window, window + 1):
        candidate = _hotp(secret, counter + offset, digits=digits)
        if hmac.compare_digest(candidate, code):
            return True
    return False


def build_provisioning_uri(
    secret_b32: str,
    *,
    account_name: str,
    issuer: str = "ContentFlow",
    digits: int = 6,
    period: int = 30,
) -> str:
    """Return an ``otpauth://`` URI suitable for QR-code provisioning."""
    label = quote(f"{issuer}:{account_name}")
    params = (
        f"secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&algorithm=SHA1"
        f"&digits={digits}"
        f"&period={period}"
    )
    return f"otpauth://totp/{label}?{params}"


# ─── Enrollment helpers ────────────────────────────────────────────────────


@dataclass
class EnrollmentPackage:
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


def start_enrollment(account_name: str, *, issuer: str = "ContentFlow") -> EnrollmentPackage:
    secret = generate_secret()
    codes = generate_backup_codes()
    uri = build_provisioning_uri(secret, account_name=account_name, issuer=issuer)
    return EnrollmentPackage(secret=secret, provisioning_uri=uri, backup_codes=codes)


def consume_backup_code(codes: list[str] | None, candidate: str) -> tuple[bool, list[str]]:
    """Return (ok, updated_codes) — single-use semantics, case-insensitive match."""
    if not codes:
        return False, codes or []
    normalized = candidate.strip().upper()
    remaining = list(codes)
    for idx, code in enumerate(remaining):
        if hmac.compare_digest(code.upper(), normalized):
            remaining.pop(idx)
            return True, remaining
    return False, remaining
