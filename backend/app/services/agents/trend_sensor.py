"""Trend Sensor Agent — Niche-aware trend detection from platform APIs."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.intelligence.models import (
    Trend, TrendStatus, TrendType, SourceRegistry,
)
from app.core.logging import get_logger
from app.services.intelligence.velocity_engine import calculate_velocity

logger = get_logger(__name__)


async def scan_niche_trends(
    db: AsyncSession,
    niche_id: UUID,
) -> dict[str, Any]:
    """Scan trends for a specific niche.
    
    Queries platform APIs based on niche keywords and updates trend matrix.
    
    Args:
        db: Database session
        niche_id: Niche to scan trends for
        
    Returns:
        dict with scan statistics
    """
    from app.domains.control.models import Niche
    from app.services.intelligence.platform_adapters import fetch_all_trends
    
    stats = {
        "niche_id": str(niche_id),
        "trends_found": 0,
        "trends_updated": 0,
        "trends_new": 0,
        "spike_events": 0,
    }
    
    # Get niche details
    result = await db.execute(
        select(Niche).where(Niche.id == niche_id)
    )
    niche = result.scalar_one_or_none()
    
    if not niche:
        logger.warning("niche_not_found", niche_id=str(niche_id))
        return stats
    
    # Get niche keywords
    keywords = niche.keywords or []
    if not keywords:
        logger.warning("no_keywords_for_niche", niche_id=str(niche_id))
        return stats
    
    # Fetch trends from all platforms
    try:
        trend_data_list = await fetch_all_trends(niche_id, keywords)
    except Exception as e:
        logger.error(
            "trend_fetch_failed",
            niche_id=str(niche_id),
            error=str(e),
        )
        return stats
    
    for trend_data in trend_data_list:
        # Check if trend exists
        result = await db.execute(
            select(Trend).where(
                Trend.title == trend_data["title"],
                Trend.platform == trend_data["platform"],
                Trend.niche_id == niche_id,
            )
        )
        existing_trend = result.scalar_one_or_none()
        
        if existing_trend:
            # Update existing trend
            velocity_result = await calculate_velocity(
                db, existing_trend.id, trend_data["score"]
            )
            stats["trends_updated"] += 1
            
            if velocity_result["should_alert"]:
                stats["spike_events"] += 1
                # Trigger spike event (handled by Celery task)
                from app.workers.tasks import dispatch_trend_insights
                dispatch_trend_insights.delay(str(existing_trend.id))
        else:
            # Create new trend
            new_trend = Trend(
                niche_id=niche_id,
                platform=trend_data["platform"],
                trend_type=TrendType(trend_data["type"]),
                title=trend_data["title"],
                description=trend_data.get("description"),
                hashtags=trend_data.get("hashtags", []),
                example_urls=trend_data.get("example_urls", []),
                trend_score=trend_data["score"],
                trend_velocity=0.0,
                status=TrendStatus.RISING,
                started_at=datetime.now(timezone.utc),
                source=trend_data.get("source", "api"),
            )
            db.add(new_trend)
            stats["trends_new"] += 1
        
        stats["trends_found"] += 1
    
    await db.commit()
    
    logger.info("niche_trends_scanned", **stats)
    return stats
