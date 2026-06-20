"""Synthesis Agent — Maps trends to workspace niches and generates custom insights."""
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.intelligence.models import (
    Trend, WorkspaceInsight, InsightType,
)
from app.domains.control.models import Workspace
from app.core.logging import get_logger
from app.integrations.llm.provider import create_llm_provider_from_settings, TaskType

logger = get_logger(__name__)


async def synthesize_trend_insights(
    db: AsyncSession,
    trend_id: UUID,
) -> dict[str, int]:
    """Generate workspace-specific insights for a trending topic.
    
    Iterates over workspaces subscribed to the trend's niche and generates
    custom actionable insights using Claude 3.5 Sonnet.
    
    Args:
        db: Database session
        trend_id: Trend that spiked
        
    Returns:
        dict with synthesis statistics
    """
    stats = {"workspaces_processed": 0, "insights_generated": 0, "errors": 0}
    
    # Get trend
    result = await db.execute(select(Trend).where(Trend.id == trend_id))
    trend = result.scalar_one_or_none()
    
    if not trend or not trend.niche_id:
        logger.error("trend_not_found_or_no_niche", trend_id=str(trend_id))
        return stats
    
    # Get workspaces with this niche
    result = await db.execute(
        select(Workspace).where(
            Workspace.niche_ids.contains([trend.niche_id])
        )
    )
    workspaces = result.scalars().all()
    
    provider = create_llm_provider_from_settings()

    # (workspace_id, title, body, insight_id) tuples — dispatched only AFTER a
    # successful commit so we never notify users about a rolled-back insight.
    pending_pushes: list[tuple[str, str, str, str]] = []

    for workspace in workspaces:
        try:
            # Generate custom insight
            prompt = f"""A new trend '{trend.title}' is spiking on {trend.platform}.

The user is a creator in the '{workspace.name}' workspace focusing on their niche.

Generate a highly actionable 1-paragraph push notification (max 150 words) explaining:
1. Why this trend matters for their content
2. How they can use it today
3. A 3-second hook suggestion for a short-form video

Be specific, actionable, and urgent."""

            response = await provider.complete(
                task_type=TaskType.GENERATION,
                messages=[{"role": "user", "content": prompt}],
                workspace_id=workspace.id,
                db_session=db,
            )
            
            insight_body = response.content.strip()
            
            # Create WorkspaceInsight
            insight = WorkspaceInsight(
                workspace_id=workspace.id,
                agent_type="synthesis_agent",
                insight_type=InsightType.TREND_ALERT,
                title=f"🔥 Trending: {trend.title}",
                body=insight_body,
                action_type="create_content",
                action_data={
                    "trend_id": str(trend.id),
                    "platform": trend.platform,
                    "hashtags": trend.hashtags or [],
                },
                priority=9,  # High priority for trend alerts
                expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
                metadata_={
                    "trend_score": float(trend.trend_score),
                    "trend_velocity": float(trend.trend_velocity),
                },
            )
            db.add(insight)
            await db.flush()  # populate insight.id before we reference it

            stats["insights_generated"] += 1
            stats["workspaces_processed"] += 1

            pending_pushes.append((
                str(workspace.id),
                f"🔥 Trending: {trend.title}",
                insight_body[:100] + "...",
                str(insight.id),
            ))

        except Exception as e:
            logger.error(
                "synthesis_failed",
                workspace_id=str(workspace.id),
                trend_id=str(trend_id),
                error=str(e),
            )
            stats["errors"] += 1
            continue
    
    await db.commit()

    # Only now that insights are durably persisted, dispatch notifications.
    from app.workers.tasks import send_expo_push
    for workspace_id, title, body, insight_id in pending_pushes:
        send_expo_push.delay(
            workspace_id=workspace_id,
            title=title,
            body=body,
            data={"type": "trend_alert", "insight_id": insight_id},
        )

    logger.info("trend_insights_synthesized", **stats)
    return stats
