"""Stripe Billing Adapter - Handles subscription lifecycle."""
import structlog
from typing import Optional
import stripe
from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)

PRICE_IDS = {
    "pro_monthly": "price_pro_monthly",
    "pro_yearly": "price_pro_yearly",
    "business_monthly": "price_business_monthly",
    "business_yearly": "price_business_yearly",
}

async def create_checkout_session(
    workspace_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    customer_email: Optional[str] = None
) -> str:
    """Create Stripe Checkout session."""
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email,
            metadata={"workspace_id": workspace_id},
            subscription_data={"metadata": {"workspace_id": workspace_id}},
        )
        log.info("checkout_session_created", workspace_id=workspace_id, session_id=session.id)
        return session.url
    except stripe.error.StripeError as e:
        log.error("checkout_session_failed", workspace_id=workspace_id, error=str(e))
        raise

async def create_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """Create Stripe Customer Portal session."""
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        log.info("portal_session_created", customer_id=stripe_customer_id)
        return session.url
    except stripe.error.StripeError as e:
        log.error("portal_session_failed", customer_id=stripe_customer_id, error=str(e))
        raise

async def get_subscription(subscription_id: str) -> dict:
    """Retrieve subscription details from Stripe."""
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "customer": subscription.customer,
        }
    except stripe.error.StripeError as e:
        log.error("subscription_retrieve_failed", subscription_id=subscription_id, error=str(e))
        raise
