"""Competitor Intelligence Agent - Knows what competitors post and what works.

Runs: Every 4 hours
Does: Scrapes profiles, tracks posts, identifies content gaps, generates "steal and improve" briefs
"""
from datetime import datetime, timezone
import structlog
from app.runtime.context import RunContext

log = structlog.get_logger(__name__)

async def monitor_competitors(ctx: RunContext) -> dict:
    """Monitor competitor activity and generate insights."""
    from app.db.session import AsyncSessionLocal
    from app.domains.intelligence.models import (
        CompetitorProfile, CompetitorObservation, WorkspaceInsight, InsightType
    )
    from sqlalchemy import select
    
    observations_created = 0
    insights_created = 0
    
    async with AsyncSessionLocal() as db:
        # Get active competitors for this workspace
        result = await db.execute(
            select(CompetitorProfile).where(
                CompetitorProfile.workspace_id == ctx.workspace_id,
                CompetitorProfile.is_active == True,
            )
        )
        competitors = result.scalars().all()
        
        for competitor in competitors:
            # Simulate scraping (replace with real Playwright scraping)
            new_posts = [
                {
                    "platform_post_id": f"post_{datetime.now().timestamp()}",
                    "content_type": "reel",
                    "caption": "Sample competitor post",
                    "engagement": {"likes": 5000, "comments": 250, "shares": 120},
                    "viral_score": 78.5,
                }
            ]
            
            for post_data in new_posts:
                observation = CompetitorObservation(
                    competitor_id=competitor.id,
                    observation_type="post",
                    platform_post_id=post_data["platform_post_id"],
                    content_type=post_data["content_type"],
                    caption=post_data["caption"],
                    engagement_metrics=post_data["engagement"],
                    viral_score=post_data["viral_score"],
                    ai_analysis="Strong hook in first 3 seconds. Used trending audio.",
                    content_gaps=["Didn't explain the 'why'", "No CTA"],
                    posted_at=datetime.now(timezone.utc),
                )
                db.add(observation)
                observations_created += 1
                
                # Generate insight if viral
                if post_data["viral_score"] > 70:
                    insight = WorkspaceInsight(
                        workspace_id=ctx.workspace_id,
                        agent_type="competitor_intelligence",
                        insight_type=InsightType.COMPETITOR_MOVE,
                        title=f"🔥 {competitor.display_name or competitor.platform_username} went viral",
                        body=f"Their {post_data['content_type']} got {post_data['engagement']['likes']} likes. "
                             f"Analysis: {observation.ai_analysis}. "
                             f"Opportunity: {', '.join(post_data['content_gaps'])}",
                        priority=9,
                        action_type="create_content",
                        action_data={"competitor_id": str(competitor.id)},
                    )
                    db.add(insight)
                    insights_created += 1
        
        await db.commit()
    
    log.info("competitor_monitoring_complete", 
             observations=observations_created, 
             insights=insights_created,
             workspace_id=str(ctx.workspace_id))
    return {"observations": observations_created, "insights": insights_created}
