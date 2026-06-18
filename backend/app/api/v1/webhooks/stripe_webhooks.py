"""Stripe webhook handler."""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog
import stripe
from datetime import datetime, timezone

from app.db.session import AsyncSessionLocal
from app.domains.control.models import Workspace
from app.config import get_settings

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    if not webhook_secret:
        log.error("stripe_webhook_secret_missing")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        log.error("stripe_webhook_invalid_payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        log.error("stripe_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    log.info("stripe_webhook_received", event_type=event_type, event_id=event["id"])
    
    async with AsyncSessionLocal() as db:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(db, data)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(db, data)
    
    return {"status": "success"}

async def handle_checkout_completed(db: AsyncSession, session):
    """Handle successful checkout."""
    workspace_id = session.get("metadata", {}).get("workspace_id")
    if not workspace_id:
        log.warning("checkout_missing_workspace_id", session_id=session["id"])
        return
    
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace_id)
        .values(
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_status="active",
        )
    )
    await db.commit()
    
    log.info("checkout_completed", workspace_id=workspace_id, customer_id=customer_id)

async def handle_subscription_updated(db: AsyncSession, subscription):
    """Handle subscription update."""
    subscription_id = subscription["id"]
    
    result = await db.execute(
        select(Workspace).where(Workspace.stripe_subscription_id == subscription_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        log.warning("subscription_workspace_not_found", subscription_id=subscription_id)
        return
    
    from app.services.billing.plans import tier_for_price

    price_id = subscription["items"]["data"][0]["price"]["id"]
    tier = tier_for_price(price_id)
    
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(
            subscription_tier=tier,
            subscription_status=subscription["status"],
            current_period_end=datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
        )
    )
    await db.commit()
    
    log.info("subscription_updated", workspace_id=str(workspace.id), tier=tier, status=subscription["status"])

async def handle_subscription_deleted(db: AsyncSession, subscription):
    """Handle subscription cancellation."""
    subscription_id = subscription["id"]
    
    result = await db.execute(
        select(Workspace).where(Workspace.stripe_subscription_id == subscription_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        return
    
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(subscription_tier="free", subscription_status="canceled")
    )
    await db.commit()
    
    log.info("subscription_deleted", workspace_id=str(workspace.id))

async def handle_payment_failed(db: AsyncSession, invoice):
    """Handle failed payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    
    result = await db.execute(
        select(Workspace).where(Workspace.stripe_subscription_id == subscription_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        return
    
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(subscription_status="past_due")
    )
    await db.commit()
    
    log.warning("payment_failed", workspace_id=str(workspace.id))
