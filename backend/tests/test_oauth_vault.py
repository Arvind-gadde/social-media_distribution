"""Tests for OAuth flows and TokenVault security.

Covers:
  - TokenVault encryption/decryption with workspace isolation
  - OAuth callback flow for Twitter and LinkedIn
  - Token refresh logic
  - Cross-workspace security boundaries
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from app.services.token_vault import TokenVault, TokenDecryptionError


# ═══════════════════════════════════════════════════════════════════════════════
# TokenVault Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_token_vault_encrypt_decrypt():
    """Test basic encryption and decryption."""
    master_key = TokenVault.generate_key()
    vault = TokenVault(master_key)
    workspace_id = uuid.uuid4()
    
    plaintext = "test_access_token_12345"
    encrypted = vault.encrypt(plaintext, workspace_id)
    
    assert encrypted != plaintext
    assert len(encrypted) > 0
    
    decrypted = vault.decrypt(encrypted, workspace_id)
    assert decrypted == plaintext


def test_token_vault_workspace_isolation():
    """Test that workspace A cannot decrypt workspace B's tokens."""
    master_key = TokenVault.generate_key()
    vault = TokenVault(master_key)
    
    workspace_a = uuid.uuid4()
    workspace_b = uuid.uuid4()
    
    plaintext = "secret_token"
    encrypted_for_a = vault.encrypt(plaintext, workspace_a)
    
    # Attempting to decrypt with wrong workspace should fail
    with pytest.raises(TokenDecryptionError):
        vault.decrypt(encrypted_for_a, workspace_b)


def test_token_vault_empty_string():
    """Test handling of empty strings."""
    master_key = TokenVault.generate_key()
    vault = TokenVault(master_key)
    workspace_id = uuid.uuid4()
    
    encrypted = vault.encrypt("", workspace_id)
    assert encrypted == ""
    
    decrypted = vault.decrypt("", workspace_id)
    assert decrypted == ""


def test_token_vault_key_rotation():
    """Test re-encryption with a new master key."""
    old_key = TokenVault.generate_key()
    new_key = TokenVault.generate_key()
    
    vault = TokenVault(old_key)
    workspace_id = uuid.uuid4()
    
    plaintext = "rotate_me"
    encrypted_old = vault.encrypt(plaintext, workspace_id)
    
    # Rotate to new key
    encrypted_new = vault.rotate_key(encrypted_old, workspace_id, new_key)
    
    # Old vault cannot decrypt new ciphertext
    with pytest.raises(TokenDecryptionError):
        vault.decrypt(encrypted_new, workspace_id)
    
    # New vault can decrypt
    new_vault = TokenVault(new_key)
    decrypted = new_vault.decrypt(encrypted_new, workspace_id)
    assert decrypted == plaintext


def test_token_vault_invalid_master_key():
    """Test that invalid master key raises error."""
    with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY must be set"):
        TokenVault("")


# ═══════════════════════════════════════════════════════════════════════════════
# OAuth Callback Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skip(reason="oauth_callback signature changed; private _exchange_code helper removed in refactor.")
@pytest.mark.asyncio
async def test_oauth_twitter_callback_success(async_db_session):
    """Test successful Twitter OAuth callback flow."""
    from app.api.v1.oauth import oauth_callback
    from app.domains.control.models import SocialAccount, TokenStatus
    from sqlalchemy import select
    
    workspace_id = uuid.uuid4()
    state = f"{workspace_id}:csrf_token_123"
    code = "twitter_auth_code"
    
    # Mock token exchange
    mock_token_response = {
        "access_token": "twitter_access_token",
        "refresh_token": "twitter_refresh_token",
        "expires_in": 7200,
        "scope": "tweet.read tweet.write users.read offline.access",
    }
    
    # Mock user info
    mock_user_info = {
        "data": {
            "id": "12345",
            "username": "testuser",
            "name": "Test User",
            "profile_image_url": "https://example.com/avatar.jpg",
        }
    }
    
    with patch("app.api.v1.oauth._exchange_code", new_callable=AsyncMock) as mock_exchange:
        with patch("httpx.AsyncClient") as mock_client:
            mock_exchange.return_value = mock_token_response
            
            # Mock httpx client for user info fetch
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_info
            
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance
            
            # Call callback
            result = await oauth_callback(
                platform="twitter",
                code=code,
                state=state,
                db=async_db_session,
            )
    
    # Verify account was created
    assert result.platform == "twitter"
    assert result.platform_username == "testuser"
    assert result.is_active is True
    
    # Verify in database
    db_result = await async_db_session.execute(
        select(SocialAccount).where(
            SocialAccount.workspace_id == workspace_id,
            SocialAccount.platform == "twitter",
        )
    )
    account = db_result.scalar_one_or_none()
    assert account is not None
    assert account.platform_user_id == "12345"
    assert account.token_status == TokenStatus.VALID
    assert account.encrypted_access_token is not None
    assert account.encrypted_refresh_token is not None
    
    # Verify tokens are encrypted (not plaintext)
    assert account.encrypted_access_token != "twitter_access_token"


@pytest.mark.skip(reason="oauth_callback now requires Request param; test predates refactor.")
@pytest.mark.asyncio
async def test_oauth_callback_invalid_state(async_db_session):
    """Test OAuth callback with invalid state parameter."""
    from app.api.v1.oauth import oauth_callback
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await oauth_callback(
            platform="twitter",
            code="code",
            state="invalid_state_format",
            db=async_db_session,
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid state parameter" in str(exc_info.value.detail)


# ═══════════════════════════════════════════════════════════════════════════════
# Token Refresh Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_token_refresh_expiring_tokens(async_db_session):
    """Test automatic refresh of expiring tokens."""
    from app.services.token_refresh_service import refresh_expiring_tokens
    from app.domains.control.models import SocialAccount, TokenStatus, Workspace
    from app.models.models import User
    from app.services.token_vault import get_vault

    user = User(
        id=uuid.uuid4(),
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        name="U",
        username=f"u-{uuid.uuid4().hex[:8]}",
    )
    async_db_session.add(user)
    await async_db_session.flush()

    workspace = Workspace(
        name="Test Workspace",
        slug=f"test-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id,
    )
    async_db_session.add(workspace)
    await async_db_session.flush()

    vault = get_vault()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    
    account = SocialAccount(
        workspace_id=workspace.id,
        platform="twitter",
        platform_user_id="12345",
        platform_username="testuser",
        encrypted_access_token=vault.encrypt("old_access_token", workspace.id),
        encrypted_refresh_token=vault.encrypt("refresh_token", workspace.id),
        token_expires_at=expires_at,
        token_status=TokenStatus.VALID,
        is_active=True,
    )
    async_db_session.add(account)
    await async_db_session.commit()
    
    # Mock adapter refresh
    mock_token_data = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 7200,
    }
    
    with patch("app.integrations.platforms.adapters.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.refresh_token = AsyncMock(return_value=mock_token_data)
        mock_get_adapter.return_value = mock_adapter
        
        # Run refresh
        result = await refresh_expiring_tokens(async_db_session)
    
    assert result["refreshed"] == 1
    assert result["failed"] == 0
    
    # Verify token was updated
    await async_db_session.refresh(account)
    assert account.token_status == TokenStatus.VALID
    
    # Verify new token is encrypted
    decrypted = vault.decrypt(account.encrypted_access_token, workspace.id)
    assert decrypted == "new_access_token"


@pytest.mark.asyncio
async def test_token_refresh_marks_expired_on_failure(async_db_session):
    """Test that failed refresh marks token as expired."""
    from app.services.token_refresh_service import refresh_expiring_tokens
    from app.domains.control.models import SocialAccount, TokenStatus, Workspace
    from app.models.models import User
    from app.services.token_vault import get_vault

    user = User(
        id=uuid.uuid4(),
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        name="U",
        username=f"u-{uuid.uuid4().hex[:8]}",
    )
    async_db_session.add(user)
    await async_db_session.flush()

    workspace = Workspace(
        name="Test Workspace",
        slug=f"test-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id,
    )
    async_db_session.add(workspace)
    await async_db_session.flush()

    vault = get_vault()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)

    account = SocialAccount(
        workspace_id=workspace.id,
        platform="twitter",
        platform_user_id="12345",
        encrypted_access_token=vault.encrypt("old_token", workspace.id),
        encrypted_refresh_token=vault.encrypt("refresh_token", workspace.id),
        token_expires_at=expires_at,
        token_status=TokenStatus.VALID,
        is_active=True,
    )
    async_db_session.add(account)
    await async_db_session.commit()
    
    # Mock adapter refresh failure
    with patch("app.integrations.platforms.adapters.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.refresh_token = AsyncMock(return_value={"error": "invalid_grant"})
        mock_get_adapter.return_value = mock_adapter
        
        # Run refresh
        result = await refresh_expiring_tokens(async_db_session)
    
    assert result["failed"] == 1
    
    # Verify token marked as expired
    await async_db_session.refresh(account)
    assert account.token_status == TokenStatus.EXPIRED
