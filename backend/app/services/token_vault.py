"""Token Vault — Fernet-based encryption for social platform tokens.

All social account tokens are encrypted at rest using a workspace-scoped
Fernet key derived from the global TOKEN_ENCRYPTION_KEY + workspace_id.

This prevents:
  - Token leaks from DB dumps
  - Cross-workspace token access (each workspace derives a unique key)

Usage:
    vault = TokenVault(settings.TOKEN_ENCRYPTION_KEY)
    encrypted = vault.encrypt(access_token, workspace_id)
    decrypted = vault.decrypt(encrypted, workspace_id)
"""
from __future__ import annotations

import base64
import hashlib
import uuid

from cryptography.fernet import Fernet, InvalidToken

import structlog

logger = structlog.get_logger(__name__)


class TokenVault:
    """Fernet-based token encryption with per-workspace key derivation."""

    def __init__(self, master_key: str) -> None:
        """Initialize vault with a master encryption key.

        Args:
            master_key: Base64-encoded 32-byte key or a passphrase.
                        If a passphrase, it's SHA-256 hashed to derive a key.
        """
        if not master_key:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be set")
        self._master_key = self._normalize_key(master_key)

    def encrypt(self, plaintext: str, workspace_id: uuid.UUID) -> str:
        """Encrypt a token string.

        Args:
            plaintext: The raw token to encrypt
            workspace_id: Workspace UUID for key derivation

        Returns:
            Base64-encoded encrypted token string
        """
        if not plaintext:
            return ""
        fernet = self._get_fernet(workspace_id)
        return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str, workspace_id: uuid.UUID) -> str:
        """Decrypt an encrypted token string.

        Args:
            ciphertext: The encrypted token
            workspace_id: Workspace UUID for key derivation

        Returns:
            Decrypted plaintext token

        Raises:
            TokenDecryptionError: If decryption fails (wrong key, corrupt data)
        """
        if not ciphertext:
            return ""
        fernet = self._get_fernet(workspace_id)
        try:
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            logger.error(
                "token_decryption_failed",
                workspace_id=str(workspace_id),
            )
            raise TokenDecryptionError(
                "Failed to decrypt token — key mismatch or corrupt data"
            ) from exc

    def rotate_key(
        self,
        ciphertext: str,
        workspace_id: uuid.UUID,
        new_master_key: str,
    ) -> str:
        """Re-encrypt a token with a new master key.

        Args:
            ciphertext: Token encrypted with the current key
            workspace_id: Workspace UUID
            new_master_key: The new master key to encrypt with

        Returns:
            Token re-encrypted with the new key
        """
        plaintext = self.decrypt(ciphertext, workspace_id)
        new_vault = TokenVault(new_master_key)
        return new_vault.encrypt(plaintext, workspace_id)

    def _get_fernet(self, workspace_id: uuid.UUID) -> Fernet:
        """Derive a workspace-specific Fernet key."""
        derived = self._derive_workspace_key(workspace_id)
        return Fernet(derived)

    def _derive_workspace_key(self, workspace_id: uuid.UUID) -> bytes:
        """Derive a unique 32-byte key per workspace using HKDF-like construction.

        master_key + workspace_id → SHA-256 → base64-encode → Fernet key
        """
        material = self._master_key + str(workspace_id).encode("utf-8")
        digest = hashlib.sha256(material).digest()
        return base64.urlsafe_b64encode(digest)

    @staticmethod
    def _normalize_key(raw: str) -> bytes:
        """Normalize a raw key string to bytes.

        Accepts either a base64 key or a passphrase.
        """
        raw_bytes = raw.encode("utf-8")
        # If it's already a valid 32-byte base64, use it directly
        try:
            decoded = base64.urlsafe_b64decode(raw_bytes)
            if len(decoded) == 32:
                return raw_bytes
        except Exception:
            pass
        # Otherwise, hash to produce 32 bytes
        return hashlib.sha256(raw_bytes).digest()

    @staticmethod
    def generate_key() -> str:
        """Generate a new random Fernet-compatible master key.

        Returns:
            Base64-encoded 32-byte key string for use as TOKEN_ENCRYPTION_KEY
        """
        return Fernet.generate_key().decode("utf-8")


class TokenDecryptionError(Exception):
    """Raised when token decryption fails."""
    pass


# ─── Singleton accessor ──────────────────────────────────────────────────────

_vault_instance: TokenVault | None = None


def get_vault() -> TokenVault:
    """Get or create the global TokenVault singleton."""
    global _vault_instance
    if _vault_instance is None:
        from app.config import get_settings
        _vault_instance = TokenVault(get_settings().TOKEN_ENCRYPTION_KEY)
    return _vault_instance
