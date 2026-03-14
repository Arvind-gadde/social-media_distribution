"""Unit tests for JWT and encryption utilities."""
import pytest
import time
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, encrypt_token, decrypt_token,
)
from app.exceptions import AuthenticationError


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token("user-123")
        payload = decode_token(token, "access")
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token("user-abc")
        payload = decode_token(token, "refresh")
        assert payload["sub"] == "user-abc"
        assert payload["type"] == "refresh"

    def test_wrong_type_raises(self):
        token = create_access_token("user-123")
        with pytest.raises(AuthenticationError, match="Expected refresh"):
            decode_token(token, "refresh")

    def test_invalid_token_raises(self):
        with pytest.raises(AuthenticationError):
            decode_token("not.a.valid.token", "access")

    def test_tampered_token_raises(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(AuthenticationError):
            decode_token(tampered, "access")

    def test_token_has_jti(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert "jti" in payload and len(payload["jti"]) > 0


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = '{"access_token": "secret123", "user_id": "456"}'
        encrypted = encrypt_token(original)
        assert encrypted != original
        decrypted = decrypt_token(encrypted)
        assert decrypted == original

    def test_encrypted_value_is_different_each_time(self):
        val = "same_input"
        enc1 = encrypt_token(val)
        enc2 = encrypt_token(val)
        # Fernet uses a random IV — ciphertexts should differ
        assert enc1 != enc2

    def test_decrypt_garbage_raises(self):
        with pytest.raises(AuthenticationError):
            decrypt_token("notvalidciphertext")
