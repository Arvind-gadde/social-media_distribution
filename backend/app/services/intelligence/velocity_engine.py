"""Velocity Engine — Calculates trend velocity and triggers spike events."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.intelligence.models import Trend, TrendStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

VELOCITY_THRESHOLD = 10.0  # Growth per hour threshold


async def calculate_velocity(
    db: AsyncSession,
    trend_id: UUID,
    current_score: float,
) -> dict[str, Any]:
    """Calculate trend velocity and determine if spike event should trigger.
    
    Velocity = (Current Score - Previous Score) / Hours Since Last Check
    
    Returns:
        dict with velocity, should_alert, and updated trend data
    """
    result = await db.execute(
        select(Trend).where(Trend.id == trend_id)
    )
    trend = result.scalar_one_or_none()
    
    if not trend:
        logger.error("trend_not_found", trend_id=str(trend_id))
        return {"velocity": 0.0, "should_alert": False}
    
    previous_score = trend.trend_score
    last_updated = trend.updated_at
    now = datetime.now(timezone.utc)
    
    hours_elapsed = (now - last_updated).total_seconds() / 3600
    if hours_elapsed == 0:
        hours_elapsed = 0.1  # Prevent division by zero
    
    velocity = (current_score - previous_score) / hours_elapsed
    
    # Update trend
    trend.trend_score = current_score
    trend.trend_velocity = velocity
    trend.updated_at = now
    
    # Determine if spike event should trigger
    should_alert = (
        velocity > VELOCITY_THRESHOLD
        and trend.status == TrendStatus.RISING
        and current_score > 50.0  # Minimum heat score
    )
    
    await db.commit()
    
    logger.info(
        "velocity_calculated",
        trend_id=str(trend_id),
        velocity=velocity,
        current_score=current_score,
        previous_score=previous_score,
        should_alert=should_alert,
    )
    
    return {
        "velocity": velocity,
        "should_alert": should_alert,
        "trend": {
            "id": str(trend.id),
            "title": trend.title,
            "niche_id": str(trend.niche_id) if trend.niche_id else None,
            "platform": trend.platform,
            "trend_score": current_score,
            "trend_velocity": velocity,
        },
    }
