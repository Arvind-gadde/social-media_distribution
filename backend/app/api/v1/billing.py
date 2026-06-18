"""Billing API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Annotated
import structlog
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.domains.control.models import Workspace
from app.services.billing.stripe_adapter import create_checkout_session, create_portal_session
from pydantic import BaseModel

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

class CheckoutResponse(BaseModel):
    url: str

class PortalRequest(BaseModel):
    return_url: str

class PortalResponse(BaseModel):
    url: str

class UsageResponse(BaseModel):
    posts_this_month: int
    posts_limit: int
    platforms_connected: int
    platforms_limit: int

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create Stripe checkout session."""
    from app.services.billing.plans import known_price_ids

    if request.price_id not in known_price_ids():
        raise HTTPException(status_code=400, detail="Unknown price_id")

    result = await db.execute(
        select(Workspace).where(Workspace.id == current_user.workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    url = await create_checkout_session(
        workspace_id=str(workspace.id),
        price_id=request.price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        customer_email=current_user.email,
    )

    return CheckoutResponse(url=url)


@router.get("/plans")
async def list_plans():
    """Return the configured Stripe plans + their internal tier mapping."""
    from app.services.billing.plans import PLANS

    return {
        "plans": [
            {
                "key": p.key,
                "tier": p.tier,
                "interval": p.interval,
                "display_name": p.display_name,
                "price_id": p.price_id,
            }
            for p in PLANS
        ]
    }

@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create Stripe customer portal session."""
    result = await db.execute(
        select(Workspace).where(Workspace.id == current_user.workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace or not workspace.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer found")
    
    url = await create_portal_session(
        stripe_customer_id=workspace.stripe_customer_id,
        return_url=request.return_url,
    )
    
    return PortalResponse(url=url)

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current usage vs limits."""
    from app.domains.execution.models import PublishJob
    from app.domains.control.models import SocialAccount
    from app.services.billing.entitlements import TIER_FEATURES
    from datetime import datetime, timezone
    from dateutil.relativedelta import relativedelta
    
    result = await db.execute(
        select(Workspace).where(Workspace.id == current_user.workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    tier = workspace.subscription_tier or "free"
    limits = TIER_FEATURES.get(tier, TIER_FEATURES["free"])
    
    # Count posts this month
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(PublishJob).where(
            PublishJob.workspace_id == workspace.id,
            PublishJob.created_at >= month_start,
        )
    )
    posts_this_month = len(result.scalars().all())
    
    # Count connected platforms
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.workspace_id == workspace.id,
            SocialAccount.is_active == True,
        )
    )
    platforms_connected = len(result.scalars().all())
    
    return UsageResponse(
        posts_this_month=posts_this_month,
        posts_limit=limits["max_posts_per_month"],
        platforms_connected=platforms_connected,
        platforms_limit=limits["max_platforms"],
    )
