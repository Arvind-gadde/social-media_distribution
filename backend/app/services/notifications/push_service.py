"""Push Notification Service — Expo Push API integration."""
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

logger = structlog.get_logger(__name__)

# Rate limiting: max 2 trend alerts per day per workspace
DAILY_TREND_ALERT_LIMIT = 2


async def send_push_notification(
    db: AsyncSession,
    workspace_id: UUID,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send push notification via Expo Push API.
    
    Args:
        db: Database session
        workspace_id: Target workspace
        title: Notification title
        body: Notification body
        data: Additional data payload
        
    Returns:
        dict with send status
    """
    # Check rate limit
    if not await _check_rate_limit(db, workspace_id, data):
        logger.warning(
            "push_rate_limited",
            workspace_id=str(workspace_id),
            notification_type=data.get("type") if data else None,
        )
        return {"sent": False, "reason": "rate_limited"}
    
    # Get device tokens for workspace users
    device_tokens = await _get_device_tokens(db, workspace_id)
    
    if not device_tokens:
        logger.info("no_device_tokens", workspace_id=str(workspace_id))
        return {"sent": False, "reason": "no_tokens"}
    
    # Send via Expo Push API
    try:
        from exponent_server_sdk import (
            DeviceNotRegisteredError,
            PushClient,
            PushMessage,
            PushServerError,
            PushTicketError,
        )
        
        client = PushClient()
        messages = [
            PushMessage(
                to=token,
                title=title,
                body=body,
                data=data or {},
                sound="default",
                priority="high",
            )
            for token in device_tokens
        ]
        
        # Send messages
        response = client.publish_multiple(messages)
        
        # Handle errors
        for push_response in response:
            try:
                push_response.validate_response()
            except DeviceNotRegisteredError:
                # Mark token as inactive
                await _deactivate_token(db, push_response.push_message.to)
            except PushTicketError as e:
                logger.error(
                    "push_ticket_error",
                    token=push_response.push_message.to,
                    error=str(e),
                )
        
        logger.info(
            "push_sent",
            workspace_id=str(workspace_id),
            title=title,
            token_count=len(device_tokens),
        )
        
        return {
            "sent": True,
            "token_count": len(device_tokens),
            "title": title,
        }
        
    except PushServerError as e:
        logger.error(
            "push_server_error",
            workspace_id=str(workspace_id),
            error=str(e),
        )
        return {"sent": False, "reason": "server_error", "error": str(e)}
    except Exception as e:
        logger.error(
            "push_send_failed",
            workspace_id=str(workspace_id),
            error=str(e),
        )
        return {"sent": False, "reason": "api_error", "error": str(e)}


async def _check_rate_limit(
    db: AsyncSession,
    workspace_id: UUID,
    data: dict[str, Any] | None,
) -> bool:
    """Check if workspace is within rate limits for this notification type."""
    if not data or data.get("type") != "trend_alert":
        return True  # No rate limit for non-trend alerts
    
    # TODO: Query notification history and check count
    # For now, allow all
    return True


async def _get_device_tokens(
    db: AsyncSession,
    workspace_id: UUID,
) -> list[str]:
    """Get Expo push tokens for workspace users."""
    from app.domains.notifications.models import DeviceToken
    
    result = await db.execute(
        select(DeviceToken.token).where(
            DeviceToken.workspace_id == workspace_id,
            DeviceToken.is_active == True,
        )
    )
    tokens = [row[0] for row in result.all()]
    
    # Update last_used_at
    if tokens:
        from datetime import datetime, timezone
        await db.execute(
            select(DeviceToken).where(
                DeviceToken.workspace_id == workspace_id,
                DeviceToken.is_active == True,
            )
        )
        # Bulk update would be more efficient but this is simpler
        for token in tokens:
            result = await db.execute(
                select(DeviceToken).where(DeviceToken.token == token)
            )
            device = result.scalar_one_or_none()
            if device:
                device.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    
    return tokens


async def register_device_token(
    db: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    token: str,
    platform: str | None = None,
    device_name: str | None = None,
) -> dict[str, Any]:
    """Register Expo push token for a user/workspace.
    
    Args:
        db: Database session
        user_id: User ID
        workspace_id: Workspace ID
        token: Expo push token
        platform: ios or android
        device_name: Device name
        
    Returns:
        dict with registration status
    """
    from app.domains.notifications.models import DeviceToken
    from datetime import datetime, timezone
    
    # Check if token already exists
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == user_id,
            DeviceToken.token == token,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing token
        existing.is_active = True
        existing.workspace_id = workspace_id
        existing.platform = platform or existing.platform
        existing.device_name = device_name or existing.device_name
        existing.last_used_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Create new token
        device_token = DeviceToken(
            user_id=user_id,
            workspace_id=workspace_id,
            token=token,
            platform=platform,
            device_name=device_name,
            last_used_at=datetime.now(timezone.utc),
        )
        db.add(device_token)
    
    await db.commit()
    
    logger.info(
        "device_token_registered",
        user_id=str(user_id),
        workspace_id=str(workspace_id),
        platform=platform,
    )
    
    return {"registered": True, "token": token}


async def _deactivate_token(
    db: AsyncSession,
    token: str,
) -> None:
    """Deactivate a device token that is no longer registered."""
    from app.domains.notifications.models import DeviceToken
    
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == token)
    )
    device = result.scalar_one_or_none()
    
    if device:
        device.is_active = False
        await db.commit()
        logger.info("device_token_deactivated", token=token[:20] + "...")
