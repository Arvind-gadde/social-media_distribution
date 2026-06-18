"""Token encryption service for secure OAuth token storage."""
from __future__ import annotations

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.logging import get_logger

log = get_logger(__name__)


class TokenVault:
    """Secure token encryption/decryption service."""
    
    def __init__(self):
        self._fernet = self._get_fernet()
    
    def _get_fernet(self) -> Fernet:
        """Get Fernet encryption instance."""
        # Get encryption key from environment
        encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY")
        
        if not encryption_key:
            # Generate a key from a password (in production, use a proper key)
            password = os.getenv("SECRET_KEY", "default-secret-key").encode()
            salt = b"contentflow-salt"  # In production, use a random salt
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
        else:
            key = encryption_key.encode()
        
        return Fernet(key)
    
    def encrypt(self, token: str) -> str:
        """Encrypt a token for secure storage."""
        if not token:
            return ""
        
        try:
            encrypted_bytes = self._fernet.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            log.error("token.encrypt.failed", error=str(e))
            raise ValueError(f"Failed to encrypt token: {str(e)}")
    
    def decrypt(self, encrypted_token: str) -> str:
        """Decrypt a token for use."""
        if not encrypted_token:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            log.error("token.decrypt.failed", error=str(e))
            raise ValueError(f"Failed to decrypt token: {str(e)}")
    
    def is_encrypted(self, token: str) -> bool:
        """Check if a token appears to be encrypted."""
        if not token:
            return False
        
        try:
            # Try to decode as base64 - encrypted tokens should be base64 encoded
            base64.urlsafe_b64decode(token.encode())
            return True
        except Exception:
            return False