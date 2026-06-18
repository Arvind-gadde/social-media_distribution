#!/usr/bin/env python3
"""Generate secure encryption keys for ContentFlow Phase 6.

Usage:
    python generate_keys.py
"""
from cryptography.fernet import Fernet


def main():
    print("=" * 70)
    print("ContentFlow Phase 6 - Secure Key Generation")
    print("=" * 70)
    print()
    
    # Generate TOKEN_ENCRYPTION_KEY
    token_key = Fernet.generate_key().decode()
    print("TOKEN_ENCRYPTION_KEY (for .env):")
    print(f"TOKEN_ENCRYPTION_KEY={token_key}")
    print()
    
    print("Add this to your backend/.env file")
    print()
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("  1. Never commit this key to version control")
    print("  2. Store securely in production (AWS Secrets Manager, etc.)")
    print("  3. If this key changes, ALL stored tokens become invalid")
    print("  4. Back up this key before rotating")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
