"""Competitor Spy Agent — monitors competitor accounts and detects content gaps.

From grok.md §2 "The Spy":
  The user inputs competitors. This agent scrapes their recent posts,
  analyzes top-performing content, and suggests ways to improve or
  "steal like an artist."

Responsibilities:
  - Fetch recent competitor activity (via platform APIs or scraping)
  - Analyze posting patterns, content types, engagement rates
  - Detect content gaps — topics competitors aren't covering
  - Generate "outsmart" suggestions
  - Track metric changes over time

Runs daily via Celery beat at 6:00 AM.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.intelligence.models import (
    CompetitorProfile,
    CompetitorObservation,
)
from app.domains.control.models import OutboxEvent, OutboxStatus

logger = structlog.get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def monitor_competitors_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> int:
    """Monitor all active competitors for a workspace.

    Returns the number of new observations created.
    """
    result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.workspace_id == workspace_id,
            CompetitorProfile.is_active == True,
        )
    )
    competitors = result.scalars().all()

    if not competitors:
        return 0

    total_observations = 0

    for competitor in competitors:
        try:
            observations = await _monitor_single_competitor(
                db, workspace_id, competitor,
            )
            total_observations += observations

            # Update last_tracked_at
            await db.execute(
                update(CompetitorProfile)
                .where(CompetitorProfile.id == competitor.id)
                .values(last_tracked_at=_utcnow())
            )
        except Exception as exc:
            logger.error(
                "competitor_monitor_individual_failed",
                competitor=competitor.platform_username,
                platform=competitor.platform,
                error=str(exc),
            )

    if total_observations > 0:
        await db.commit()
        logger.info(
            "competitor_monitoring_complete",
            workspace_id=str(workspace_id),
            competitors=len(competitors),
            observations=total_observations,
        )

    return total_observations


async def _monitor_single_competitor(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor: CompetitorProfile,
) -> int:
    """Monitor a single competitor account.

    Fetches recent activity using platform-specific adapters
    and creates CompetitorObservation records.

    Returns count of new observations.
    """
    # Fetch recent activity
    activities = await _fetch_competitor_activity(competitor)

    if not activities:
        return 0

    new_count = 0
    for activity in activities:
        # Dedup by platform_post_id
        if activity.get("platform_post_id"):
            existing = await db.execute(
                select(CompetitorObservation.id).where(
                    CompetitorObservation.competitor_id == competitor.id,
                    CompetitorObservation.platform_post_id == activity["platform_post_id"],
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

        observation = CompetitorObservation(
            competitor_id=competitor.id,
            observation_type=activity.get("type", "post"),
            platform_post_id=activity.get("platform_post_id"),
            content_type=activity.get("content_type"),
            content_summary=activity.get("content_summary"),
            caption=activity.get("caption"),
            hashtags=activity.get("hashtags"),
            engagement_metrics=activity.get("engagement_metrics"),
            viral_score=float(activity.get("viral_score", 0.0)),
            posted_at=activity.get("posted_at"),
        )
        db.add(observation)
        new_count += 1

    # If we have enough observations, generate a periodic analysis
    if new_count > 0:
        await _maybe_emit_analysis_event(
            db, workspace_id, competitor, new_count,
        )

    return new_count


async def _fetch_competitor_activity(
    competitor: CompetitorProfile,
) -> list[dict[str, Any]]:
    """Fetch recent activity from a competitor account.

    Platform-specific fetching. For now, this returns structured data
    from platform APIs. The implementation will be expanded as
    platform adapters are built.

    TODO: Implement per-platform fetchers:
      - Instagram: Graph API /media endpoint (requires business account)
      - YouTube: Data API v3 /search endpoint
      - Twitter/X: v2 tweets endpoint
      - TikTok: Research API
      - LinkedIn: Organization API

    For now, creates a metric snapshot observation from stored data
    rather than making actual API calls. The real fetchers will be
    implemented when OAuth flows are complete.
    """
    now = _utcnow()

    # Create a metric snapshot observation
    # Real implementation will fetch from platform APIs
    return [{
        "type": "metric_snapshot",
        "platform_post_id": None,
        "content_type": "metric_snapshot",
        "content_summary": (
            f"Periodic metric snapshot for @{competitor.platform_username} "
            f"on {competitor.platform}"
        ),
        "engagement_metrics": {
            "followers": competitor.followers_count,
            "avg_engagement_rate": competitor.avg_engagement_rate,
            "posting_frequency": competitor.posting_frequency,
            "snapshot_at": now.isoformat(),
        },
        "viral_score": 0.0,
        "posted_at": now,
    }]


async def _maybe_emit_analysis_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor: CompetitorProfile,
    new_observations: int,
) -> None:
    """Emit an outbox event for competitor analysis if enough data accumulated."""
    # Check if we have enough observations for analysis (at least 5)
    result = await db.execute(
        select(func.count(CompetitorObservation.id)).where(
            CompetitorObservation.competitor_id == competitor.id,
            CompetitorObservation.created_at >= _utcnow() - timedelta(days=7),
        )
    )
    recent_count = result.scalar() or 0

    if recent_count >= 5:
        outbox_event = OutboxEvent(
            workspace_id=workspace_id,
            event_type="competitor.analysis_ready",
            aggregate_type="competitor_profile",
            aggregate_id=str(competitor.id),
            payload={
                "workspace_id": str(workspace_id),
                "competitor_id": str(competitor.id),
                "platform": competitor.platform,
                "username": competitor.platform_username,
                "observations_count": recent_count,
            },
            status=OutboxStatus.PENDING,
        )
        db.add(outbox_event)


async def analyze_competitor_content_gaps(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    competitor_id: uuid.UUID,
    llm_provider=None,
) -> dict[str, Any]:
    """Run AI analysis on competitor observations to find content gaps.

    Uses the LLM provider to analyze patterns in competitor content
    and identify opportunities the workspace creator can exploit.

    Args:
        db: Database session
        workspace_id: Current workspace
        competitor_id: Competitor to analyze
        llm_provider: Optional LLMProvider for AI analysis

    Returns:
        Dict with content gaps, posting patterns, and suggestions
    """
    # Get competitor and recent observations
    comp_result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.workspace_id == workspace_id,
        )
    )
    competitor = comp_result.scalar_one_or_none()
    if not competitor:
        return {"error": "Competitor not found"}

    obs_result = await db.execute(
        select(CompetitorObservation)
        .where(
            CompetitorObservation.competitor_id == competitor_id,
            CompetitorObservation.created_at >= _utcnow() - timedelta(days=30),
        )
        .order_by(CompetitorObservation.created_at.desc())
        .limit(50)
    )
    observations = obs_result.scalars().all()

    if not observations:
        return {
            "competitor": competitor.platform_username,
            "platform": competitor.platform,
            "message": "Not enough data yet. Check back after monitoring runs.",
        }

    # Build analysis from observations
    analysis = _build_basic_analysis(competitor, observations)

    # If LLM provider available, enhance with AI analysis
    if llm_provider:
        enhanced = await _run_ai_analysis(llm_provider, competitor, observations, db)
        if enhanced:
            analysis.update(enhanced)

    return analysis


def _build_basic_analysis(
    competitor: CompetitorProfile,
    observations: list[CompetitorObservation],
) -> dict[str, Any]:
    """Build basic statistical analysis from observations."""
    post_observations = [
        o for o in observations if o.observation_type == "post"
    ]
    metric_snapshots = [
        o for o in observations if o.observation_type == "metric_snapshot"
    ]

    # Content type distribution
    content_types: dict[str, int] = {}
    for obs in post_observations:
        ct = obs.content_type or "unknown"
        content_types[ct] = content_types.get(ct, 0) + 1

    # Hashtag frequency
    hashtag_freq: dict[str, int] = {}
    for obs in post_observations:
        for tag in (obs.hashtags or []):
            hashtag_freq[tag] = hashtag_freq.get(tag, 0) + 1

    top_hashtags = sorted(
        hashtag_freq.items(), key=lambda x: x[1], reverse=True,
    )[:20]

    # Engagement analysis
    high_engagement_posts = sorted(
        post_observations,
        key=lambda o: o.viral_score, reverse=True,
    )[:5]

    # Follower trend from metric snapshots
    follower_trend = []
    for snap in metric_snapshots:
        metrics = snap.engagement_metrics or {}
        if "followers" in metrics:
            follower_trend.append({
                "date": snap.created_at.isoformat(),
                "followers": metrics["followers"],
            })

    return {
        "competitor": competitor.platform_username,
        "platform": competitor.platform,
        "total_observations": len(observations),
        "post_count": len(post_observations),
        "content_types": content_types,
        "top_hashtags": top_hashtags,
        "high_engagement_posts": [
            {
                "summary": p.content_summary,
                "viral_score": p.viral_score,
                "engagement": p.engagement_metrics,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            }
            for p in high_engagement_posts
        ],
        "follower_trend": follower_trend,
        "avg_viral_score": (
            sum(o.viral_score for o in post_observations) / len(post_observations)
            if post_observations else 0
        ),
    }


async def _run_ai_analysis(
    llm_provider,
    competitor: CompetitorProfile,
    observations: list[CompetitorObservation],
    db,
) -> dict[str, Any] | None:
    """Enhance analysis with AI-generated insights."""
    from app.integrations.llm.provider import TaskType

    post_summaries = "\n".join([
        f"- [{o.content_type}] {o.content_summary} (viral: {o.viral_score:.2f})"
        for o in observations[:20]
        if o.observation_type == "post" and o.content_summary
    ])

    if not post_summaries:
        return None

    messages = [
        {
            "role": "system",
            "content": (
                "You are a competitive intelligence analyst for content creators. "
                "Analyze competitor activity and identify actionable content gaps."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Competitor: @{competitor.platform_username} on {competitor.platform}\n"
                f"Followers: {competitor.followers_count:,}\n"
                f"Avg Engagement: {competitor.avg_engagement_rate:.2%}\n\n"
                f"Recent posts:\n{post_summaries}\n\n"
                f"Respond with JSON:\n"
                f'{{"content_gaps": ["gap 1", "gap 2"], '
                f'"posting_patterns": "summary of when/what they post", '
                f'"outsmart_suggestions": '
                f'["suggestion 1", "suggestion 2"], '
                f'"weak_spots": ["area where they underperform"]}}'
            ),
        },
    ]

    try:
        response = await llm_provider.complete(
            task_type=TaskType.ANALYSIS,
            messages=messages,
            temperature=0.5,
            max_tokens=1500,
            db_session=db,
        )
        import json
        import re
        text = re.sub(r"```json\s*|\s*```", "", response.content).strip()
        return json.loads(text)
    except Exception as exc:
        logger.warning("competitor_ai_analysis_failed", error=str(exc))
        return None
