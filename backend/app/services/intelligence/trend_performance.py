"""Trend performance tracking - Track if creators used trends and how they performed."""
import uuid
import structlog
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.domains.intelligence.models import Trend, WorkspaceInsight
from app.domains.execution.models import ContentVariant

log = structlog.get_logger(__name__)

async def track_trend_usage(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    trend_id: uuid.UUID,
    content_variant_id: uuid.UUID
) -> None:
    """Link a content variant to a trend it was based on.
    
    Args:
        db: Database session
        workspace_id: Workspace UUID
        trend_id: Trend UUID
        content_variant_id: Content variant UUID
    """
    # Update content variant metadata to include trend reference
    result = await db.execute(
        select(ContentVariant).where(ContentVariant.id == content_variant_id)
    )
    variant = result.scalar_one_or_none()
    
    if variant:
        metadata = variant.metadata_ or {}
        metadata["trend_id"] = str(trend_id)
        metadata["trend_used_at"] = datetime.now(timezone.utc).isoformat()
        
        variant.metadata_ = metadata
        await db.commit()
        
        log.info("trend_usage_tracked",
                 workspace_id=str(workspace_id),
                 trend_id=str(trend_id),
                 content_id=str(content_variant_id))

async def analyze_trend_performance(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    trend_id: uuid.UUID
) -> dict:
    """Analyze how content based on a trend performed.
    
    Args:
        db: Database session
        workspace_id: Workspace UUID
        trend_id: Trend UUID
    
    Returns:
        Performance analysis dictionary
    """
    # Find all content variants that used this trend
    result = await db.execute(
        select(ContentVariant).where(
            ContentVariant.workspace_id == workspace_id,
            ContentVariant.status == "published"
        )
    )
    variants = result.scalars().all()
    
    # Filter variants that reference this trend
    trend_variants = []
    for variant in variants:
        metadata = variant.metadata_ or {}
        if metadata.get("trend_id") == str(trend_id):
            trend_variants.append(variant)
    
    if not trend_variants:
        return {
            "used": False,
            "content_count": 0,
        }
    
    # Calculate aggregate performance
    total_views = sum(v.total_views or 0 for v in trend_variants)
    total_engagement = sum(v.total_likes or 0 for v in trend_variants) + \
                      sum(v.total_comments or 0 for v in trend_variants) + \
                      sum(v.total_shares or 0 for v in trend_variants)
    
    avg_engagement_rate = sum(v.engagement_rate or 0 for v in trend_variants) / len(trend_variants)
    
    # Get trend details
    result = await db.execute(select(Trend).where(Trend.id == trend_id))
    trend = result.scalar_one_or_none()
    
    return {
        "used": True,
        "content_count": len(trend_variants),
        "total_views": total_views,
        "total_engagement": total_engagement,
        "avg_engagement_rate": round(avg_engagement_rate, 4),
        "trend_score": trend.trend_score if trend else 0,
        "platforms_used": list(set(v.target_platform for v in trend_variants if v.target_platform)),
        "best_performing": {
            "id": str(max(trend_variants, key=lambda v: v.engagement_rate or 0).id),
            "engagement_rate": max(v.engagement_rate or 0 for v in trend_variants),
        } if trend_variants else None,
    }

async def generate_trend_roi_report(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    days: int = 30
) -> dict:
    """Generate ROI report for trend usage.
    
    Args:
        db: Database session
        workspace_id: Workspace UUID
        days: Number of days to analyze
    
    Returns:
        ROI report dictionary
    """
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all trends shown to workspace
    result = await db.execute(
        select(WorkspaceInsight).where(
            and_(
                WorkspaceInsight.workspace_id == workspace_id,
                WorkspaceInsight.insight_type == "trend_alert",
                WorkspaceInsight.created_at >= cutoff
            )
        )
    )
    insights = result.scalars().all()
    
    total_trends_shown = len(insights)
    trends_used = 0
    total_performance = 0
    
    for insight in insights:
        metadata = insight.metadata_ or {}
        trend_id = metadata.get("trend_id")
        
        if trend_id:
            perf = await analyze_trend_performance(db, workspace_id, uuid.UUID(trend_id))
            if perf["used"]:
                trends_used += 1
                total_performance += perf.get("total_engagement", 0)
    
    usage_rate = (trends_used / total_trends_shown * 100) if total_trends_shown > 0 else 0
    
    return {
        "period_days": days,
        "trends_shown": total_trends_shown,
        "trends_used": trends_used,
        "usage_rate": round(usage_rate, 2),
        "total_engagement_from_trends": total_performance,
        "avg_engagement_per_trend": round(total_performance / trends_used, 2) if trends_used > 0 else 0,
    }
