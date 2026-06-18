"""Goal & Reminder Agent — tracks creator goals and sends proactive nudges.

From grok.md §2 "The Nudge":
  Tracks the user's weekly goals. If it's Thursday and they haven't posted,
  it sends a push notification with a pre-written script to make it easy.

Responsibilities:
  - Check goal progress (weekly/monthly post targets)
  - Generate motivational nudge messages
  - Create ready-to-use content suggestions when behind
  - Track streaks and celebrate milestones
  - Emit outbox events for push notifications

This agent runs on a Celery beat schedule (daily) and per-workspace.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.execution.models import (
    CreatorGoal, GoalCheckIn, ContentVariant, PublishJob, PublishStatus,
    GoalStatus, GoalPeriod,
)
from app.domains.control.models import OutboxEvent, OutboxStatus

logger = structlog.get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def check_goals_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Check all active goals for a workspace and generate nudges.

    Returns a list of nudge dicts for goals that are behind schedule.
    """
    # Get active goals
    result = await db.execute(
        select(CreatorGoal).where(
            CreatorGoal.workspace_id == workspace_id,
            CreatorGoal.status == GoalStatus.ACTIVE,
        )
    )
    goals = result.scalars().all()

    if not goals:
        return []

    nudges: list[dict[str, Any]] = []
    now = _utcnow()

    for goal in goals:
        progress = await _calculate_progress(db, workspace_id, goal, now)

        if progress["needs_nudge"]:
            nudge = {
                "goal_id": str(goal.id),
                "goal_type": goal.period,
                "target": goal.target_value,
                "achieved": progress["achieved"],
                "remaining": progress["remaining"],
                "period_progress_pct": progress["period_progress_pct"],
                "achievement_pct": progress["achievement_pct"],
                "message": progress["nudge_message"],
                "urgency": progress["urgency"],
                "streak": progress.get("streak", 0),
            }
            nudges.append(nudge)

            # Record check-in
            check_in = GoalCheckIn(
                goal_id=goal.id,
                value_at_checkin=float(progress["achieved"]),
                progress_pct=float(progress["achievement_pct"]),
                note=progress["nudge_message"],
            )
            db.add(check_in)

            # Emit outbox event for push notification
            outbox_event = OutboxEvent(
                workspace_id=workspace_id,
                event_type="goal.nudge",
                aggregate_type="creator_goal",
                aggregate_id=str(goal.id),
                payload={
                    "workspace_id": str(workspace_id),
                    "goal_type": goal.period,
                    "message": progress["nudge_message"],
                    "urgency": progress["urgency"],
                    "achievement_pct": progress["achievement_pct"],
                },
                status=OutboxStatus.PENDING,
            )
            db.add(outbox_event)

    if nudges:
        await db.commit()
        logger.info(
            "goal_nudges_generated",
            workspace_id=str(workspace_id),
            nudge_count=len(nudges),
        )

    return nudges


async def _calculate_progress(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    goal: CreatorGoal,
    now: datetime,
) -> dict[str, Any]:
    """Calculate goal progress and determine if a nudge is needed."""
    # Determine period boundaries
    if goal.period == "weekly":
        period_start = now - timedelta(days=now.weekday())
        period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=7)
        days_elapsed = (now - period_start).days
        total_days = 7
    elif goal.period == "monthly":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (period_start + timedelta(days=32)).replace(day=1)
        period_end = next_month
        days_elapsed = (now - period_start).days
        total_days = (period_end - period_start).days
    else:
        # Daily goals
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
        days_elapsed = 0
        total_days = 1

    # Count published content in this period
    result = await db.execute(
        select(func.count(PublishJob.id)).where(
            PublishJob.workspace_id == workspace_id,
            PublishJob.status == PublishStatus.COMPLETED,
            PublishJob.completed_at >= period_start,
            PublishJob.completed_at < period_end,
        )
    )
    achieved = result.scalar() or 0

    target = goal.target_value
    remaining = max(0, target - achieved)
    period_progress_pct = round((days_elapsed / max(total_days, 1)) * 100, 1)
    achievement_pct = round((achieved / max(target, 1)) * 100, 1)

    # Determine if nudge is needed
    needs_nudge = False
    urgency = "low"
    nudge_message = ""

    if achieved >= target:
        # Goal met — celebrate!
        if achievement_pct == 100:
            nudge_message = (
                f"🎉 You've hit your {goal.period} target of {target} posts! "
                f"Keep the momentum going!"
            )
            # Still flag as nudge for celebration notification
            needs_nudge = True
            urgency = "celebration"
    elif period_progress_pct >= 70 and achievement_pct < 60:
        # Behind schedule — urgent
        needs_nudge = True
        urgency = "high"
        days_left = max(1, total_days - days_elapsed)
        nudge_message = (
            f"⚠️ You're falling behind! Only {achieved}/{target} posts done "
            f"with {days_left} day(s) left this {goal.period[:-2] if goal.period.endswith('ly') else goal.period}. "
            f"Need {remaining} more — I can help you draft something right now!"
        )
    elif period_progress_pct >= 50 and achievement_pct < 30:
        # Halfway through period, less than 30% done
        needs_nudge = True
        urgency = "medium"
        nudge_message = (
            f"📊 Halfway check: {achieved}/{target} posts this {goal.period[:-2] if goal.period.endswith('ly') else goal.period}. "
            f"You need {remaining} more to stay on track. "
            f"Want me to suggest some content ideas?"
        )
    elif days_elapsed == 0 and goal.period == "weekly":
        # Start of week — fresh start nudge
        needs_nudge = True
        urgency = "low"
        nudge_message = (
            f"🌟 New week! Your goal: {target} posts. "
            f"I've got trending topics in your niche ready for you."
        )

    return {
        "achieved": achieved,
        "remaining": remaining,
        "period_progress_pct": period_progress_pct,
        "achievement_pct": achievement_pct,
        "needs_nudge": needs_nudge,
        "urgency": urgency,
        "nudge_message": nudge_message,
    }


async def get_goal_summary(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> dict[str, Any]:
    """Get a comprehensive goal summary for the workspace dashboard."""
    result = await db.execute(
        select(CreatorGoal).where(
            CreatorGoal.workspace_id == workspace_id,
            CreatorGoal.status == GoalStatus.ACTIVE,
        )
    )
    goals = result.scalars().all()

    now = _utcnow()
    summaries = []

    for goal in goals:
        progress = await _calculate_progress(db, workspace_id, goal, now)
        summaries.append({
            "goal_id": str(goal.id),
            "goal_type": goal.period,
            "target": goal.target_value,
            "achieved": progress["achieved"],
            "remaining": progress["remaining"],
            "period_progress_pct": progress["period_progress_pct"],
            "achievement_pct": progress["achievement_pct"],
            "on_track": progress["achievement_pct"] >= progress["period_progress_pct"],
        })

    return {
        "workspace_id": str(workspace_id),
        "goals": summaries,
        "overall_on_track": all(s["on_track"] for s in summaries) if summaries else True,
    }
