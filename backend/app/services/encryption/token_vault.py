"""Compatibility shim for the canonical TokenVault.

This module previously contained a SECOND, divergent TokenVault that derived a
Fernet key from a hardcoded ``"default-secret-key"`` passphrase and a static
salt whenever ``TOKEN_ENCRYPTION_KEY`` was unset. Any token encrypted under
that fallback was trivially decryptable by anyone with the source. That
insecure implementation has been removed.

The single, hardened vault lives in ``app.services.token_vault`` (fails closed
on a missing key, derives a unique key per workspace). Import from here only
for backwards compatibility — prefer importing ``app.services.token_vault``
directly in new code.
"""
from __future__ import annotations

from app.services.token_vault import TokenVault, TokenDecryptionError, get_vault

__all__ = ["TokenVault", "TokenDecryptionError", "get_vault"]
