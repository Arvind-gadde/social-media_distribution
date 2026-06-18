"""Analytics API — dashboard stats, engagement metrics, usage reporting.

Workspace-scoped analytics system.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, desc

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.execution.models import (
    AnalyticsFact, ContentVariant, ContentProject, PublishJob, PublishStatus,
)
from app.domains.control.models import UsageMeter, SocialAccount

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard_stats(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    days: int = Query(30, ge=1, le=365),
) -> JSONResponse:
    """Get workspace dashboard analytics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total content projects
    projects_result = await db.execute(
        select(func.count(ContentProject.id)).where(
            and_(
                ContentProject.workspace_id == workspace.id,
                ContentProject.deleted_at.is_(None),
            )
        )
    )
    total_projects = projects_result.scalar() or 0

    # Total content variants
    variants_result = await db.execute(
        select(func.count(ContentVariant.id)).where(
            ContentVariant.workspace_id == workspace.id,
        )
    )
    total_variants = variants_result.scalar() or 0

    # Published in period
    published_result = await db.execute(
        select(func.count(PublishJob.id)).where(
            and_(
                PublishJob.workspace_id == workspace.id,
                PublishJob.status == PublishStatus.COMPLETED,
                PublishJob.completed_at >= cutoff,
            )
        )
    )
    published_count = published_result.scalar() or 0

    # Total views/likes/engagement from analytics facts
    engagement_result = await db.execute(
        select(
            func.coalesce(func.sum(AnalyticsFact.views), 0),
            func.coalesce(func.sum(AnalyticsFact.likes), 0),
            func.coalesce(func.sum(AnalyticsFact.comments), 0),
            func.coalesce(func.sum(AnalyticsFact.shares), 0),
            func.coalesce(func.sum(AnalyticsFact.saves), 0),
        ).where(
            and_(
                AnalyticsFact.workspace_id == workspace.id,
                AnalyticsFact.recorded_at >= cutoff,
            )
        )
    )
    eng = engagement_result.one()
    total_views, total_likes, total_comments, total_shares, total_saves = eng

    # Connected accounts
    accounts_result = await db.execute(
        select(func.count(SocialAccount.id)).where(
            and_(
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.is_active == True,
            )
        )
    )
    connected_accounts = accounts_result.scalar() or 0

    # LLM spend in period
    spend_result = await db.execute(
        select(func.coalesce(func.sum(UsageMeter.cost_usd), 0.0)).where(
            and_(
                UsageMeter.workspace_id == workspace.id,
                UsageMeter.recorded_at >= cutoff,
            )
        )
    )
    total_spend = float(spend_result.scalar() or 0)

    return JSONResponse({
        "period_days": days,
        "content": {
            "total_projects": total_projects,
            "total_variants": total_variants,
            "published": published_count,
        },
        "engagement": {
            "total_views": int(total_views),
            "total_likes": int(total_likes),
            "total_comments": int(total_comments),
            "total_shares": int(total_shares),
            "total_saves": int(total_saves),
        },
        "platform": {
            "connected_accounts": connected_accounts,
        },
        "cost": {
            "total_spend_usd": round(total_spend, 4),
        },
    })


@router.get("/engagement")
async def engagement_metrics(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    platform: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """Get engagement metrics per content variant."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    filters = [
        AnalyticsFact.workspace_id == workspace.id,
        AnalyticsFact.recorded_at >= cutoff,
    ]
    if platform:
        filters.append(AnalyticsFact.platform == platform)

    result = await db.execute(
        select(AnalyticsFact)
        .where(and_(*filters))
        .order_by(desc(AnalyticsFact.views))
        .limit(limit)
    )
    facts = result.scalars().all()

    return JSONResponse({
        "metrics": [
            {
                "id": str(f.id),
                "content_variant_id": str(f.content_variant_id) if f.content_variant_id else None,
                "platform": f.platform,
                "recorded_at": f.recorded_at.isoformat(),
                "views": f.views,
                "likes": f.likes,
                "comments": f.comments,
                "shares": f.shares,
                "saves": f.saves,
                "reach": f.reach,
                "engagement_rate": f.engagement_rate,
                "completion_rate": f.completion_rate,
                "estimated_revenue_usd": f.estimated_revenue_usd,
            }
            for f in facts
        ],
        "total": len(facts),
    })


@router.get("/usage")
async def usage_metrics(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    days: int = Query(30, ge=1, le=365),
) -> JSONResponse:
    """Get workspace usage and cost metrics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Group by meter type
    result = await db.execute(
        select(
            UsageMeter.meter_type,
            func.sum(UsageMeter.quantity).label("total_quantity"),
            func.sum(UsageMeter.cost_usd).label("total_cost"),
            func.count(UsageMeter.id).label("event_count"),
        )
        .where(
            and_(
                UsageMeter.workspace_id == workspace.id,
                UsageMeter.recorded_at >= cutoff,
            )
        )
        .group_by(UsageMeter.meter_type)
        .order_by(desc("total_cost"))
    )
    rows = result.all()

    # Group by provider
    provider_result = await db.execute(
        select(
            UsageMeter.provider,
            func.sum(UsageMeter.cost_usd).label("total_cost"),
            func.count(UsageMeter.id).label("call_count"),
        )
        .where(
            and_(
                UsageMeter.workspace_id == workspace.id,
                UsageMeter.recorded_at >= cutoff,
                UsageMeter.provider.isnot(None),
            )
        )
        .group_by(UsageMeter.provider)
        .order_by(desc("total_cost"))
    )
    provider_rows = provider_result.all()

    return JSONResponse({
        "period_days": days,
        "by_type": [
            {
                "meter_type": row.meter_type,
                "total_quantity": float(row.total_quantity or 0),
                "total_cost_usd": round(float(row.total_cost or 0), 4),
                "event_count": int(row.event_count or 0),
            }
            for row in rows
        ],
        "by_provider": [
            {
                "provider": row.provider or "unknown",
                "total_cost_usd": round(float(row.total_cost or 0), 4),
                "call_count": int(row.call_count or 0),
            }
            for row in provider_rows
        ],
        "total_spend_usd": round(sum(float(r.total_cost or 0) for r in rows), 4),
    })


@router.get("/platform-breakdown")
async def platform_breakdown(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    days: int = Query(30, ge=1, le=365),
) -> JSONResponse:
    """Get analytics breakdown by platform."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            AnalyticsFact.platform,
            func.sum(AnalyticsFact.views).label("total_views"),
            func.sum(AnalyticsFact.likes).label("total_likes"),
            func.sum(AnalyticsFact.comments).label("total_comments"),
            func.sum(AnalyticsFact.shares).label("total_shares"),
            func.avg(AnalyticsFact.engagement_rate).label("avg_engagement"),
            func.count(AnalyticsFact.id).label("post_count"),
        )
        .where(
            and_(
                AnalyticsFact.workspace_id == workspace.id,
                AnalyticsFact.recorded_at >= cutoff,
            )
        )
        .group_by(AnalyticsFact.platform)
        .order_by(desc("total_views"))
    )
    rows = result.all()

    return JSONResponse({
        "period_days": days,
        "platforms": [
            {
                "platform": row.platform,
                "total_views": int(row.total_views or 0),
                "total_likes": int(row.total_likes or 0),
                "total_comments": int(row.total_comments or 0),
                "total_shares": int(row.total_shares or 0),
                "avg_engagement_rate": round(float(row.avg_engagement or 0), 4),
                "post_count": int(row.post_count or 0),
            }
            for row in rows
        ],
    })
