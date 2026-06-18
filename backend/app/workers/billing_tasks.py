"""Celery tasks for Stripe billing synchronization and reconciliation.

Phase 11: SaaS Monetization
"""
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.domains.control.models import Workspace
from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


@celery_app.task(name="app.workers.tasks.sync_all_stripe_customers", time_limit=1800)
def sync_all_stripe_customers():
    """Daily reconciliation of Stripe subscriptions.
    
    Runs daily at 3 AM. A failsafe that queries Stripe API to ensure our local
    'subscription_status' perfectly matches Stripe's records, healing any missed webhooks.
    
    This is critical for:
    - Healing missed webhook events
    - Detecting subscription changes made directly in Stripe dashboard
    - Ensuring billing accuracy
    """
    import asyncio
    asyncio.run(_sync_all_stripe_customers_async())


async def _sync_all_stripe_customers_async():
    """Async implementation of Stripe customer sync."""
    if not settings.has_stripe:
        log.warning("stripe_sync_skipped", reason="Stripe not configured")
        return
    
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    log.info("stripe_sync_started")
    
    synced_count = 0
    error_count = 0
    updated_count = 0
    
    async with AsyncSessionLocal() as db:
        # Get all workspaces with Stripe customer IDs
        result = await db.execute(
            select(Workspace).where(Workspace.stripe_customer_id.isnot(None))
        )
        workspaces = result.scalars().all()
        
        log.info("stripe_sync_workspaces_found", count=len(workspaces))
        
        for workspace in workspaces:
            try:
                # Fetch subscription from Stripe
                if workspace.stripe_subscription_id:
                    subscription = stripe.Subscription.retrieve(
                        workspace.stripe_subscription_id
                    )
                    
                    # Check if local state matches Stripe
                    needs_update = False
                    updates = {}
                    
                    if workspace.subscription_status != subscription.status:
                        updates["subscription_status"] = subscription.status
                        needs_update = True
                    
                    stripe_period_end = datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    )
                    if workspace.current_period_end != stripe_period_end:
                        updates["current_period_end"] = stripe_period_end
                        needs_update = True
                    
                    if workspace.cancel_at_period_end != subscription.cancel_at_period_end:
                        updates["cancel_at_period_end"] = subscription.cancel_at_period_end
                        needs_update = True
                    
                    # Determine tier from price ID
                    price_id = subscription["items"]["data"][0]["price"]["id"]
                    tier = _determine_tier_from_price(price_id)
                    if workspace.subscription_tier != tier:
                        updates["subscription_tier"] = tier
                        needs_update = True
                    
                    if needs_update:
                        await db.execute(
                            update(Workspace)
                            .where(Workspace.id == workspace.id)
                            .values(**updates)
                        )
                        updated_count += 1
                        log.info(
                            "stripe_sync_workspace_updated",
                            workspace_id=str(workspace.id),
                            updates=updates,
                        )
                
                synced_count += 1
                
            except stripe.error.StripeError as e:
                error_count += 1
                log.error(
                    "stripe_sync_workspace_failed",
                    workspace_id=str(workspace.id),
                    error=str(e),
                )
            except Exception as e:
                error_count += 1
                log.error(
                    "stripe_sync_workspace_error",
                    workspace_id=str(workspace.id),
                    error=str(e),
                )
        
        await db.commit()
    
    log.info(
        "stripe_sync_completed",
        synced=synced_count,
        updated=updated_count,
        errors=error_count,
    )


def _determine_tier_from_price(price_id: str) -> str:
    """Determine subscription tier from Stripe price ID."""
    if price_id in (settings.PRICE_PRO_MONTHLY, settings.PRICE_PRO_YEARLY):
        return "pro"
    elif price_id in (settings.PRICE_BUSINESS_MONTHLY, settings.PRICE_BUSINESS_YEARLY):
        return "business"
    else:
        return "free"


@celery_app.task(name="app.workers.tasks.handle_subscription_expiry")
def handle_subscription_expiry():
    """Check for expired subscriptions and downgrade to free tier.
    
    Runs hourly. Checks for subscriptions where current_period_end has passed
    and subscription_status is 'canceled' or 'past_due' for > 7 days.
    """
    import asyncio
    asyncio.run(_handle_subscription_expiry_async())


async def _handle_subscription_expiry_async():
    """Async implementation of subscription expiry handling."""
    log.info("subscription_expiry_check_started")
    
    now = datetime.now(timezone.utc)
    downgraded_count = 0
    
    async with AsyncSessionLocal() as db:
        # Find workspaces with expired subscriptions
        result = await db.execute(
            select(Workspace).where(
                Workspace.current_period_end < now,
                Workspace.subscription_status.in_(["canceled", "past_due"]),
                Workspace.subscription_tier != "free",
            )
        )
        expired_workspaces = result.scalars().all()
        
        for workspace in expired_workspaces:
            await db.execute(
                update(Workspace)
                .where(Workspace.id == workspace.id)
                .values(
                    subscription_tier="free",
                    subscription_status="canceled",
                )
            )
            downgraded_count += 1
            log.info(
                "workspace_downgraded_to_free",
                workspace_id=str(workspace.id),
                previous_tier=workspace.subscription_tier,
            )
        
        await db.commit()
    
    log.info(
        "subscription_expiry_check_completed",
        downgraded=downgraded_count,
    )
