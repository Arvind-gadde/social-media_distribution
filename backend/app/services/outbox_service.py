"""Outbox Service - Durable event delivery pattern.

Phase 12: Audit & Governance
Use cases:
- send notification
- trigger operator alert
- sync analytics rollup
- export billing event
- invoke external integration

Never rely on "write DB row and hope another service noticed".
"""
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domains.control.models import OutboxEvent, OutboxStatus
from app.runtime.correlation import get_correlation_id

log = structlog.get_logger(__name__)


class OutboxService:
    """Service for durable event delivery."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Optional[dict[str, Any]] = None,
        workspace_id: Optional[uuid.UUID] = None,
        max_attempts: int = 5,
    ) -> OutboxEvent:
        """Create an outbox event for async delivery.
        
        Args:
            event_type: Type of event (e.g., "notification.send", "analytics.sync")
            aggregate_type: Type of aggregate (e.g., "publish_job", "agent_run")
            aggregate_id: ID of the aggregate
            payload: Event payload
            workspace_id: Workspace context (if applicable)
            max_attempts: Maximum delivery attempts
        
        Returns:
            Created OutboxEvent instance
        """
        correlation_id = get_correlation_id()
        
        outbox_event = OutboxEvent(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            correlation_id=correlation_id,
            status=OutboxStatus.PENDING,
            next_attempt_at=datetime.now(timezone.utc),
            attempt_count=0,
            max_attempts=max_attempts,
            created_at=datetime.now(timezone.utc),
        )
        
        self.db.add(outbox_event)
        await self.db.flush()
        
        log.info(
            "outbox_event_created",
            event_id=str(outbox_event.id),
            event_type=event_type,
            aggregate_type=aggregate_type,
            workspace_id=str(workspace_id) if workspace_id else None,
            correlation_id=correlation_id,
        )
        
        return outbox_event
    
    async def get_pending_events(
        self,
        limit: int = 100,
    ) -> list[OutboxEvent]:
        """Get pending events ready for delivery.
        
        Args:
            limit: Maximum number of events to fetch
        
        Returns:
            List of pending outbox events
        """
        now = datetime.now(timezone.utc)
        
        query = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]),
                OutboxEvent.next_attempt_at <= now,
            )
            .order_by(OutboxEvent.next_attempt_at.asc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def mark_dispatched(
        self,
        event_id: uuid.UUID,
    ) -> None:
        """Mark an event as successfully dispatched.
        
        Args:
            event_id: Event ID
        """
        await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status=OutboxStatus.DISPATCHED,
                dispatched_at=datetime.now(timezone.utc),
            )
        )
        
        log.info("outbox_event_dispatched", event_id=str(event_id))
    
    async def mark_failed(
        self,
        event_id: uuid.UUID,
        error_message: str,
        retry_delay_seconds: int = 60,
    ) -> None:
        """Mark an event as failed and schedule retry.
        
        Args:
            event_id: Event ID
            error_message: Error description
            retry_delay_seconds: Seconds until next retry
        """
        query = select(OutboxEvent).where(OutboxEvent.id == event_id)
        result = await self.db.execute(query)
        event = result.scalar_one_or_none()
        
        if not event:
            return
        
        event.attempt_count += 1
        event.last_error = error_message
        
        if event.attempt_count >= event.max_attempts:
            event.status = OutboxStatus.DEAD_LETTER
            log.error(
                "outbox_event_dead_letter",
                event_id=str(event_id),
                attempts=event.attempt_count,
                error=error_message,
            )
        else:
            event.status = OutboxStatus.FAILED
            event.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=retry_delay_seconds * (2 ** event.attempt_count)  # Exponential backoff
            )
            log.warning(
                "outbox_event_failed",
                event_id=str(event_id),
                attempt=event.attempt_count,
                next_attempt=event.next_attempt_at.isoformat(),
                error=error_message,
            )
        
        await self.db.flush()
    
    async def process_pending(self, batch_size: int = 100) -> dict[str, int]:
        """Dispatch pending outbox events with retry/dead-letter semantics."""
        events = await self.get_pending_events(limit=batch_size)
        stats = {"processed": 0, "dispatched": 0, "failed": 0}

        for event in events:
            stats["processed"] += 1
            try:
                await self._dispatch_event(event)
                await self.mark_dispatched(event.id)
                stats["dispatched"] += 1
            except Exception as exc:
                await self.mark_failed(event.id, str(exc))
                stats["failed"] += 1
            await self.db.commit()

        return stats

    async def _dispatch_event(self, event: OutboxEvent) -> None:
        """Dispatch one outbox event to its concrete handler."""
        if event.event_type == "notification.send":
            await self._dispatch_notification(event)
            return

        if event.event_type == "analytics.sync":
            await self._dispatch_analytics_sync(event)
            return

        if event.event_type == "webhook.deliver":
            await self._dispatch_webhook(event)
            return

        if event.event_type.startswith("webhook.") and event.event_type.endswith(".received"):
            await self._dispatch_platform_webhook_received(event)
            return

        raise ValueError(f"No outbox dispatcher registered for {event.event_type}")

    async def _dispatch_notification(self, event: OutboxEvent) -> None:
        """Create an in-app notification from an outbox event."""
        from app.domains.execution.models import Notification

        payload = event.payload or {}
        user_id = payload.get("user_id")
        title = payload.get("title")
        if not event.workspace_id:
            raise ValueError("notification.send requires workspace_id")
        if not user_id:
            raise ValueError("notification.send requires payload.user_id")
        if not title:
            raise ValueError("notification.send requires payload.title")

        notification = Notification(
            workspace_id=event.workspace_id,
            user_id=uuid.UUID(str(user_id)),
            type=payload.get("notification_type", "system"),
            title=str(title),
            body=payload.get("body"),
            data=payload.get("data") or {},
            sent_at=datetime.now(timezone.utc),
        )
        self.db.add(notification)
        await self.db.flush()

    async def _dispatch_analytics_sync(self, event: OutboxEvent) -> None:
        """Run analytics sync for the event workspace."""
        if not event.workspace_id:
            raise ValueError("analytics.sync requires workspace_id")

        from app.services.analytics_sync import sync_analytics_for_workspace

        await sync_analytics_for_workspace(self.db, event.workspace_id)

    async def _dispatch_webhook(self, event: OutboxEvent) -> None:
        """Deliver a webhook event to an external URL."""
        import httpx

        payload = event.payload or {}
        webhook_url = payload.get("webhook_url")
        event_data = payload.get("event_data")
        if not webhook_url:
            raise ValueError("webhook.deliver requires payload.webhook_url")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                str(webhook_url),
                json=event_data or {},
                headers={
                    "Content-Type": "application/json",
                    "X-ContentFlow-Event": event.event_type,
                    "X-ContentFlow-Delivery": str(event.id),
                },
            )
            response.raise_for_status()

    async def _dispatch_platform_webhook_received(self, event: OutboxEvent) -> None:
        """Reconcile an inbound platform webhook with its ContentVariant.

        Parses the receipt's payload via :mod:`webhook_reconciliation`, updates
        engagement counters monotonically, and marks the receipt PROCESSED.
        """
        from app.domains.control.models import (
            WebhookProcessingStatus,
            WebhookReceipt,
        )
        from app.services.webhook_reconciliation import reconcile_receipt

        payload = event.payload or {}
        receipt_id = payload.get("receipt_id") or event.aggregate_id
        result = await self.db.execute(
            select(WebhookReceipt).where(WebhookReceipt.id == uuid.UUID(str(receipt_id)))
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise ValueError(f"Webhook receipt not found: {receipt_id}")

        reconciliation = await reconcile_receipt(self.db, receipt)
        log.info(
            "webhook_reconciled",
            receipt_id=str(receipt.id),
            platform=receipt.provider,
            matched=reconciliation.matched,
            metrics_keys=list(reconciliation.metrics.keys()),
        )

        receipt.processing_status = WebhookProcessingStatus.PROCESSED
        receipt.processed_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def retry_dead_letter(
        self,
        event_id: uuid.UUID,
    ) -> None:
        """Manually retry a dead-letter event.
        
        Args:
            event_id: Event ID
        """
        await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status=OutboxStatus.PENDING,
                next_attempt_at=datetime.now(timezone.utc),
                attempt_count=0,
                last_error=None,
            )
        )
        
        log.info("outbox_event_retried", event_id=str(event_id))


# Convenience functions for common event types

async def emit_notification_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> OutboxEvent:
    """Emit a notification event."""
    service = OutboxService(db)
    
    return await service.create_event(
        event_type="notification.send",
        aggregate_type="notification",
        aggregate_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        payload={
            "user_id": str(user_id),
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "data": data,
        },
    )


async def emit_analytics_sync_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    platform: str,
    account_id: uuid.UUID,
) -> OutboxEvent:
    """Emit an analytics sync event."""
    service = OutboxService(db)
    
    return await service.create_event(
        event_type="analytics.sync",
        aggregate_type="social_account",
        aggregate_id=str(account_id),
        workspace_id=workspace_id,
        payload={
            "platform": platform,
            "account_id": str(account_id),
        },
    )


async def emit_billing_export_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
) -> OutboxEvent:
    """Emit a billing export event."""
    service = OutboxService(db)
    
    return await service.create_event(
        event_type="billing.export",
        aggregate_type="workspace",
        aggregate_id=str(workspace_id),
        workspace_id=workspace_id,
        payload={
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
    )


async def emit_webhook_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    webhook_url: str,
    event_data: dict,
) -> OutboxEvent:
    """Emit a webhook delivery event."""
    service = OutboxService(db)
    
    return await service.create_event(
        event_type="webhook.deliver",
        aggregate_type="webhook",
        aggregate_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        payload={
            "webhook_url": webhook_url,
            "event_data": event_data,
        },
    )
