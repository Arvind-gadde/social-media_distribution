"""Token refresh service — proactively refreshes expiring social account tokens.

Runs as a daily Celery task. Finds tokens expiring within 24h and
refreshes them via platform APIs, re-encrypting with TokenVault.

If refresh fails, marks the account as TOKEN_EXPIRED so the user
is prompted to re-authorize.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import SocialAccount, TokenStatus
from app.services.token_vault import get_vault

logger = structlog.get_logger(__name__)

# Refresh tokens expiring within this window
REFRESH_WINDOW = timedelta(hours=24)


async def refresh_expiring_tokens(db: AsyncSession) -> dict[str, int]:
    """Find and refresh tokens expiring within the next 24 hours.

    Returns summary of refreshed/failed counts.
    """
    now = datetime.now(timezone.utc)
    expiry_cutoff = now + REFRESH_WINDOW

    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.is_active == True,
            SocialAccount.token_status == TokenStatus.VALID,
            SocialAccount.token_expires_at.isnot(None),
            SocialAccount.token_expires_at <= expiry_cutoff,
            SocialAccount.encrypted_refresh_token.isnot(None),
        )
        .order_by(SocialAccount.token_expires_at.asc())
        .limit(100)
    )
    accounts = result.scalars().all()

    if not accounts:
        return {"refreshed": 0, "failed": 0, "total": 0}

    refreshed = 0
    failed = 0

    for account in accounts:
        try:
            success = await _refresh_single_account(db, account)
            if success:
                refreshed += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error(
                "token_refresh_crash",
                account_id=str(account.id),
                platform=account.platform,
                error=str(exc),
            )
            failed += 1

    await db.commit()

    logger.info(
        "token_refresh_complete",
        refreshed=refreshed,
        failed=failed,
        total=len(accounts),
    )

    return {"refreshed": refreshed, "failed": failed, "total": len(accounts)}


async def _refresh_single_account(
    db: AsyncSession,
    account: SocialAccount,
) -> bool:
    """Refresh tokens for a single account.

    Returns True if successful, False otherwise.
    """
    vault = get_vault()

    # Decrypt refresh token
    refresh_token = vault.decrypt(
        account.encrypted_refresh_token,
        account.workspace_id,
    )
    if not refresh_token:
        logger.warning(
            "no_refresh_token",
            account_id=str(account.id),
            platform=account.platform,
        )
        return False

    # Call platform refresh endpoint
    from app.integrations.platforms.adapters import get_adapter

    # Decrypt current access token for adapter init
    access_token = vault.decrypt(
        account.encrypted_access_token,
        account.workspace_id,
    )

    from app.config import get_settings
    settings = get_settings()

    extra_kwargs = _get_platform_extras(account.platform, settings)

    try:
        adapter = get_adapter(
            platform=account.platform,
            access_token=access_token,
            **extra_kwargs,
        )
    except ValueError:
        return False

    token_data = await adapter.refresh_token(refresh_token)

    if "error" in token_data:
        logger.warning(
            "token_refresh_failed",
            account_id=str(account.id),
            platform=account.platform,
            error=token_data["error"],
        )
        # Mark as expired
        account.token_status = TokenStatus.EXPIRED
        return False

    new_access = token_data.get("access_token", "")
    new_refresh = token_data.get("refresh_token", refresh_token)  # Some platforms reuse
    expires_in = token_data.get("expires_in")

    if not new_access:
        account.token_status = TokenStatus.EXPIRED
        return False

    # Re-encrypt and save
    account.encrypted_access_token = vault.encrypt(new_access, account.workspace_id)
    if new_refresh != refresh_token:
        account.encrypted_refresh_token = vault.encrypt(new_refresh, account.workspace_id)

    if expires_in:
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    account.token_status = TokenStatus.VALID
    account.last_validated_at = datetime.now(timezone.utc)

    logger.info(
        "token_refreshed",
        account_id=str(account.id),
        platform=account.platform,
    )
    return True


def _get_platform_extras(platform: str, settings: Any) -> dict[str, str]:
    """Get platform-specific kwargs for adapter initialization."""
    if platform == "instagram":
        return {
            "app_id": settings.FACEBOOK_APP_ID,
            "app_secret": settings.FACEBOOK_APP_SECRET,
        }
    elif platform == "twitter":
        return {"client_id": settings.TWITTER_API_KEY}
    elif platform == "linkedin":
        return {
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        }
    elif platform == "youtube":
        return {
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        }
    return {}
