"""Tests for the MFA / TOTP service module.

Validation uses the published RFC 6238 test vectors so the implementation is
provably interoperable with standard authenticator apps.
"""
from __future__ import annotations

import time

import pytest

from app.services import mfa_service


def test_generate_secret_is_base32_and_sized():
    secret = mfa_service.generate_secret()
    assert len(secret) >= 32  # 20 bytes b32-encoded = 32 chars
    # base32 chars only
    assert all(ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for ch in secret)


def test_backup_codes_are_unique_and_dashed():
    codes = mfa_service.generate_backup_codes(count=10)
    assert len(codes) == 10
    assert len(set(codes)) == 10
    for code in codes:
        assert "-" in code
        assert len(code) == 9  # 4 + 1 dash + 4


def test_rfc6238_test_vector_sha1():
    # RFC 6238 Appendix B: secret = ASCII "12345678901234567890".
    # Base32 of that string is "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ".
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    # Unix time 59  → 8-digit code "94287082"; truncate to 6 → "287082".
    assert mfa_service.generate_totp(secret, for_time=59, digits=6) == "287082"
    # Unix time 1111111109 → "081804".
    assert mfa_service.generate_totp(secret, for_time=1111111109, digits=6) == "081804"


def test_verify_totp_accepts_current_code():
    secret = mfa_service.generate_secret()
    now = int(time.time())
    code = mfa_service.generate_totp(secret, for_time=now)
    assert mfa_service.verify_totp(secret, code, for_time=now) is True


def test_verify_totp_allows_one_step_drift():
    secret = mfa_service.generate_secret()
    code_then = mfa_service.generate_totp(secret, for_time=1_000)
    # Verifier looks one step ahead by default.
    assert mfa_service.verify_totp(secret, code_then, for_time=1_000 + 25) is True


def test_verify_totp_rejects_wrong_code():
    secret = mfa_service.generate_secret()
    assert mfa_service.verify_totp(secret, "000000") is False
    assert mfa_service.verify_totp(secret, "12345") is False  # wrong length
    assert mfa_service.verify_totp(secret, "abcdef") is False  # non-digit


def test_provisioning_uri_contains_required_params():
    uri = mfa_service.build_provisioning_uri(
        "JBSWY3DPEHPK3PXP",
        account_name="ada@example.com",
        issuer="ContentFlow",
    )
    assert uri.startswith("otpauth://totp/ContentFlow%3Aada%40example.com")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=ContentFlow" in uri
    assert "algorithm=SHA1" in uri


def test_consume_backup_code_marks_as_used():
    codes = ["AAAA-1111", "BBBB-2222", "CCCC-3333"]
    ok, remaining = mfa_service.consume_backup_code(codes, "bbbb-2222")
    assert ok is True
    assert "BBBB-2222" not in remaining
    assert len(remaining) == 2


def test_consume_backup_code_rejects_unknown():
    codes = ["AAAA-1111"]
    ok, remaining = mfa_service.consume_backup_code(codes, "ZZZZ-9999")
    assert ok is False
    assert remaining == codes


def test_start_enrollment_returns_full_package():
    pkg = mfa_service.start_enrollment("ada@example.com")
    assert pkg.secret
    assert pkg.provisioning_uri.startswith("otpauth://")
    assert len(pkg.backup_codes) == 10
