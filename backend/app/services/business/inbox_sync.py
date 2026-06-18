"""DM Inbox Sync Service — Fetches DMs from platform APIs.

Iterates over SocialAccount records and fetches messages since last_synced_at.
Stores raw messages in DMInbox for AI evaluation.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.business.models import DMInbox
from app.domains.control.models import SocialAccount, TokenStatus
from app.services.token_vault import get_vault
from app.runtime.context import RunContext

logger = logging.getLogger(__name__)


async def sync_workspace_dms(
    db: AsyncSession,
    ctx: RunContext,
) -> dict[str, int]:
    """Sync DMs for all active social accounts in workspace.
    
    Returns:
        Dict with counts: {"fetched": 10, "new": 5, "errors": 0}
    """
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.workspace_id == ctx.workspace_id,
            SocialAccount.is_active == True,
            SocialAccount.token_status == TokenStatus.VALID,
        )
    )
    accounts = result.scalars().all()
    
    stats = {"fetched": 0, "new": 0, "errors": 0}
    vault = get_vault()
    
    for account in accounts:
        try:
            # Decrypt token
            access_token = vault.decrypt(
                account.encrypted_access_token,
                ctx.workspace_id,
            )
            
            # Fetch DMs based on platform
            messages = await _fetch_platform_dms(
                platform=account.platform,
                access_token=access_token,
                since=account.last_synced_at,
            )
            
            stats["fetched"] += len(messages)
            
            # Store new messages
            for msg in messages:
                # Check if already exists
                existing = await db.execute(
                    select(DMInbox).where(
                        DMInbox.platform == account.platform,
                        DMInbox.platform_message_id == msg.get("id"),
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                dm = DMInbox(
                    workspace_id=ctx.workspace_id,
                    social_account_id=account.id,
                    platform=account.platform,
                    platform_message_id=msg.get("id"),
                    sender_platform_id=msg["sender"]["id"],
                    sender_username=msg["sender"]["username"],
                    sender_display_name=msg["sender"].get("display_name"),
                    sender_avatar_url=msg["sender"].get("avatar_url"),
                    sender_followers_count=msg["sender"].get("followers_count"),
                    message_text=msg["text"],
                    message_metadata=msg.get("metadata"),
                    received_at=msg.get("timestamp", datetime.now(timezone.utc)),
                )
                db.add(dm)
                stats["new"] += 1
            
            # Update last_synced_at
            account.last_synced_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(
                f"Failed to sync DMs for account {account.id}: {e}",
                extra={"workspace_id": str(ctx.workspace_id), "account_id": str(account.id)},
            )
            stats["errors"] += 1
    
    await db.commit()
    return stats


async def _fetch_platform_dms(
    platform: str,
    access_token: str,
    since: datetime | None,
) -> list[dict]:
    """Fetch DMs from platform API.
    
    Note: This is a stub. Real implementation requires platform-specific clients.
    Twitter: GET /2/dm_conversations/:id/dm_events
    Instagram: GET /{ig-user-id}/conversations (requires Business account)
    """
    # TODO: Implement platform-specific DM fetching
    # For now, return empty list
    logger.warning(f"DM fetching not yet implemented for platform: {platform}")
    return []
