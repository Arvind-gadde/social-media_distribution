"""Goal & Accountability Agent - Digital coach that doesn't let creators slack.

Runs: Daily check-in + event-triggered
Does: Monitors progress, sends smart reminders, calculates catch-up plans
"""
from datetime import datetime, timezone, timedelta
import structlog
from app.runtime.context import RunContext

log = structlog.get_logger(__name__)

async def check_goals(ctx: RunContext) -> dict:
    """Check goal progress and send reminders if needed."""
    from app.db.session import AsyncSessionLocal
    from app.domains.intelligence.models import WorkspaceInsight, InsightType
    from sqlalchemy import select, and_
    import uuid
    
    insights_created = 0
    
    async with AsyncSessionLocal() as db:
        # Simulate goal checking (replace with real goal queries)
        goals_behind = [
            {"title": "Weekly Posts Goal", "current": 2, "target": 5, "unit": "posts"},
            {"title": "Follower Growth", "current": 150, "target": 500, "unit": "followers"},
        ]
        
        for goal in goals_behind:
            progress_pct = (goal["current"] / goal["target"]) * 100
            
            if progress_pct < 60:  # Behind schedule
                insight = WorkspaceInsight(
                    workspace_id=ctx.workspace_id,
                    agent_type="goal_accountability",
                    insight_type=InsightType.GOAL_WARNING,
                    title=f"⚠️ Behind on {goal['title']}",
                    body=f"You're at {goal['current']}/{goal['target']} {goal['unit']} ({progress_pct:.0f}%). "
                         f"Post {goal['target'] - goal['current']} more this week to catch up!",
                    priority=8,
                    action_type="create_content",
                    action_data={"goal_type": goal["title"]},
                )
                db.add(insight)
                insights_created += 1
        
        await db.commit()
    
    log.info("goal_check_complete", insights_created=insights_created, workspace_id=str(ctx.workspace_id))
    return {"insights_created": insights_created}
