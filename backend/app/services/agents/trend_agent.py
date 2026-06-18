"""Trend Detection Agent - Catches trends before they peak.

Runs: Every 30 minutes
Sources: TikTok, Twitter, YouTube, Reddit, Instagram, Pinterest
Does: Scores trends 0-100, predicts peak timing, matches to niche
"""
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
import structlog
from app.runtime.context import RunContext

log = structlog.get_logger(__name__)

PLATFORMS = ["tiktok", "twitter", "youtube", "reddit", "instagram"]

async def detect_trends(ctx: RunContext, niche_ids: list[str]) -> dict:
    """Detect rising trends across platforms."""
    from app.db.session import AsyncSessionLocal
    from app.domains.intelligence.models import Trend, TrendType, TrendStatus
    from sqlalchemy import select
    import uuid
    
    trends_found = []
    
    # Simulate trend detection (replace with real scraping)
    sample_trends = [
        {"title": "AI Agents Going Viral", "platform": "twitter", "score": 85.0, "velocity": 12.5},
        {"title": "#ContentCreator2025", "platform": "instagram", "score": 72.0, "velocity": 8.3},
        {"title": "Short-form Video Tips", "platform": "youtube", "score": 68.0, "velocity": 5.2},
    ]
    
    async with AsyncSessionLocal() as db:
        for trend_data in sample_trends:
            # Check if trend exists
            trend_hash = hashlib.sha256(
                f"{trend_data['platform']}:{trend_data['title']}".encode()
            ).hexdigest()[:16]
            
            result = await db.execute(
                select(Trend).where(Trend.title == trend_data["title"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                trend = Trend(
                    niche_id=uuid.UUID(niche_ids[0]) if niche_ids else None,
                    platform=trend_data["platform"],
                    trend_type=TrendType.TOPIC,
                    title=trend_data["title"],
                    trend_score=trend_data["score"],
                    trend_velocity=trend_data["velocity"],
                    status=TrendStatus.RISING,
                    started_at=datetime.now(timezone.utc),
                    peak_predicted_at=datetime.now(timezone.utc) + timedelta(hours=18),
                )
                db.add(trend)
                trends_found.append(trend_data)
        
        await db.commit()
    
    log.info("trend_detection_complete", trends_found=len(trends_found), workspace_id=str(ctx.workspace_id))
    return {"trends_found": len(trends_found), "trends": trends_found}
