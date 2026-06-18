"""Entitlements - Feature gating based on subscription tier."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import Workspace

TIER_FEATURES = {
    "free": {
        "max_platforms": 3,
        "max_posts_per_month": 30,
        "agents": ["trend_detection", "goal_accountability"],
        "video_editor": False,
        "competitor_tracking": False,
        "business_agent": False,
    },
    "pro": {
        "max_platforms": 12,
        "max_posts_per_month": 300,
        "agents": ["trend_detection", "goal_accountability", "analytics_intelligence", 
                   "smart_scheduling", "niche_intelligence", "content_research"],
        "video_editor": True,
        "competitor_tracking": True,
        "business_agent": False,
    },
    "business": {
        "max_platforms": 999,
        "max_posts_per_month": 9999,
        "agents": "all",
        "video_editor": True,
        "competitor_tracking": True,
        "business_agent": True,
    },
}

def check_entitlement(workspace: Workspace, feature: str) -> bool:
    """Check if workspace has access to feature."""
    tier = workspace.subscription_tier or "free"
    features = TIER_FEATURES.get(tier, TIER_FEATURES["free"])
    
    if feature in features:
        return features[feature] if isinstance(features[feature], bool) else True
    
    if feature.startswith("agent:"):
        agent_name = feature.split(":")[1]
        allowed_agents = features.get("agents", [])
        return allowed_agents == "all" or agent_name in allowed_agents
    
    return False

def require_entitlement(workspace: Workspace, feature: str):
    """Raise exception if workspace lacks entitlement."""
    if not check_entitlement(workspace, feature):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Feature '{feature}' requires upgrade. Current tier: {workspace.subscription_tier}"
        )


def tier_limits(workspace: Workspace) -> dict[str, Any]:
    """Return the limit dict for a workspace's current tier."""
    tier = workspace.subscription_tier or "free"
    return TIER_FEATURES.get(tier, TIER_FEATURES["free"])


async def check_post_quota(
    db: AsyncSession,
    workspace: Workspace,
    *,
    additional: int = 1,
) -> tuple[bool, int, int]:
    """Return (allowed, used_this_month, limit) for ``additional`` new posts."""
    from app.domains.execution.models import PublishJob

    limits = tier_limits(workspace)
    cap = int(limits.get("max_posts_per_month", 0))

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    res = await db.execute(
        select(func.count(PublishJob.id)).where(
            PublishJob.workspace_id == workspace.id,
            PublishJob.created_at >= month_start,
        )
    )
    used = int(res.scalar() or 0)
    return used + additional <= cap, used, cap


async def enforce_post_quota(
    db: AsyncSession,
    workspace: Workspace,
    *,
    additional: int = 1,
) -> None:
    allowed, used, cap = await check_post_quota(db, workspace, additional=additional)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly post quota exceeded ({used}/{cap}). Upgrade plan to publish more.",
        )


async def check_platform_quota(
    db: AsyncSession,
    workspace: Workspace,
) -> tuple[bool, int, int]:
    """Return (allowed, connected, limit) for connecting one more platform."""
    from app.domains.control.models import SocialAccount

    limits = tier_limits(workspace)
    cap = int(limits.get("max_platforms", 0))
    res = await db.execute(
        select(func.count(SocialAccount.id)).where(
            SocialAccount.workspace_id == workspace.id,
            SocialAccount.is_active.is_(True),
        )
    )
    connected = int(res.scalar() or 0)
    return connected + 1 <= cap, connected, cap


async def enforce_platform_quota(db: AsyncSession, workspace: Workspace) -> None:
    allowed, connected, cap = await check_platform_quota(db, workspace)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Platform connection limit reached ({connected}/{cap}). Upgrade plan to add more.",
        )
