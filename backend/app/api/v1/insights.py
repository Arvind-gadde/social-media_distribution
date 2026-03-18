"""Insights API — surfaces orchestration intelligence to the dashboard.

Endpoints:
  GET  /insights/feed        — content items enriched with virality + gap signals
  GET  /insights/item/{id}   — full insight for one content item
  GET  /insights/runs        — pipeline run history (AgentRun records)
  GET  /insights/runs/{id}   — detail for a specific run
  GET  /insights/gap-picks   — only value-gap items, sorted by virality
  GET  /insights/stats        — aggregate stats for the dashboard header

All reads only — no mutations here; the orchestrator owns writes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, desc

from app.api.deps import CurrentUser, DbSession
from app.models.models import (
    ContentItem,
    ContentInsight,
    GeneratedPost,
    AgentRun,
    AgentStatus,
)

router = APIRouter(prefix="/insights", tags=["insights"])


# ─────────────────────────────────────────────────────────────────────────────
# Serialisers
# ─────────────────────────────────────────────────────────────────────────────

def _insight_to_dict(insight: ContentInsight) -> dict:
    return {
        "id": str(insight.id),
        "content_item_id": str(insight.content_item_id),
        "virality_score": insight.virality_score,
        "cross_source_count": insight.cross_source_count,
        "trend_velocity": insight.trend_velocity,
        "sentiment_breakdown": insight.sentiment_breakdown or {},
        "is_value_gap": insight.is_value_gap,
        "gap_explanation": insight.gap_explanation,
        "suggested_angle": insight.suggested_angle,
        "broll_assets": insight.broll_assets or [],
        "fact_check_passed": insight.fact_check_passed,
        "fact_check_confidence": insight.fact_check_confidence,
        "flagged_claims": insight.flagged_claims or [],
        "computed_at": insight.computed_at.isoformat(),
    }


def _item_with_insight(item: ContentItem, insight: ContentInsight | None) -> dict:
    base = {
        "id": str(item.id),
        "title": item.title,
        "source_label": item.source_label,
        "source_url": item.source_url,
        "category": item.category.value if item.category else "other",
        "relevance_score": item.relevance_score,
        "is_trending": item.is_trending,
        "summary": item.summary,
        "key_points": item.key_points or [],
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat(),
        "insight": _insight_to_dict(insight) if insight else None,
    }
    # Flatten the most-used insight fields to top-level for frontend convenience
    if insight:
        base["virality_score"] = insight.virality_score
        base["is_value_gap"] = insight.is_value_gap
        base["suggested_angle"] = insight.suggested_angle
        base["fact_check_passed"] = insight.fact_check_passed
        base["broll_assets"] = insight.broll_assets or []
    else:
        base["virality_score"] = 0.0
        base["is_value_gap"] = False
        base["suggested_angle"] = None
        base["fact_check_passed"] = None
        base["broll_assets"] = []
    return base


def _run_to_dict(run: AgentRun) -> dict:
    duration: float | None = None
    if run.started_at and run.finished_at:
        duration = round(
            (run.finished_at - run.started_at).total_seconds(), 1
        )
    return {
        "id": str(run.id),
        "triggered_by": run.triggered_by,
        "status": run.status.value if run.status else "unknown",
        "stage_timings": {
            "scout_s":    run.scout_duration_s,
            "analyst_s":  run.analyst_duration_s,
            "checker_s":  run.checker_duration_s,
            "creative_s": run.creative_duration_s,
        },
        "counts": {
            "fetched":      run.items_fetched,
            "new":          run.items_new,
            "scored":       run.items_scored,
            "fact_checked": run.items_fact_checked,
            "generated":    run.items_generated,
            "gap_signals":  run.gap_signals_found,
        },
        "stage_errors": run.stage_errors or [],
        "started_at":   run.started_at.isoformat(),
        "finished_at":  run.finished_at.isoformat() if run.finished_at else None,
        "total_duration_s": duration,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/feed")
async def get_insight_feed(
    current_user: CurrentUser,
    db: DbSession,
    hours_back: int = Query(48, ge=1, le=168),
    min_virality: float = Query(0.0, ge=0.0, le=1.0),
    value_gap_only: bool = Query(False),
    fact_check_failed: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """
    Content items joined with their insights.

    Sorted by virality_score desc, then relevance_score desc.
    Supports filtering by value_gap, virality floor, fact-check status.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    # Build the join query
    query = (
        select(ContentItem, ContentInsight)
        .outerjoin(ContentInsight, ContentInsight.content_item_id == ContentItem.id)
        .where(
            and_(
                ContentItem.is_processed == True,
                ContentItem.fetched_at >= cutoff,
            )
        )
    )

    if min_virality > 0.0:
        query = query.where(ContentInsight.virality_score >= min_virality)

    if value_gap_only:
        query = query.where(ContentInsight.is_value_gap == True)

    if fact_check_failed is not None:
        query = query.where(ContentInsight.fact_check_passed == (not fact_check_failed))

    # Sort: insight items first, by virality; then unanalysed items by relevance
    query = query.order_by(
        desc(ContentInsight.virality_score),
        desc(ContentItem.relevance_score),
        desc(ContentItem.fetched_at),
    ).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    # Count query
    count_q = (
        select(func.count(ContentItem.id))
        .outerjoin(ContentInsight, ContentInsight.content_item_id == ContentItem.id)
        .where(and_(ContentItem.is_processed == True, ContentItem.fetched_at >= cutoff))
    )
    if min_virality > 0.0:
        count_q = count_q.where(ContentInsight.virality_score >= min_virality)
    if value_gap_only:
        count_q = count_q.where(ContentInsight.is_value_gap == True)

    total = (await db.execute(count_q)).scalar() or 0

    return JSONResponse({
        "items": [_item_with_insight(item, insight) for item, insight in rows],
        "total": total,
        "filters": {
            "hours_back": hours_back,
            "min_virality": min_virality,
            "value_gap_only": value_gap_only,
        },
    })


@router.get("/gap-picks")
async def get_gap_picks(
    current_user: CurrentUser,
    db: DbSession,
    hours_back: int = Query(48, ge=1, le=168),
    limit: int = Query(10, ge=1, le=20),
) -> JSONResponse:
    """
    Value-gap items sorted by virality — the creator's priority queue.
    These are stories where the audience wants content but nobody's
    covered the angle the analyst identified.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    result = await db.execute(
        select(ContentItem, ContentInsight)
        .join(ContentInsight, ContentInsight.content_item_id == ContentItem.id)
        .where(
            and_(
                ContentItem.is_processed == True,
                ContentItem.fetched_at >= cutoff,
                ContentInsight.is_value_gap == True,
            )
        )
        .order_by(desc(ContentInsight.virality_score))
        .limit(limit)
    )
    rows = result.all()

    return JSONResponse({
        "gap_picks": [_item_with_insight(item, insight) for item, insight in rows],
        "count": len(rows),
    })


@router.get("/item/{item_id}")
async def get_item_insight(
    item_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """Full detail for one content item including all insight fields and generated posts."""
    try:
        uid = uuid.UUID(item_id)
    except ValueError:
        return JSONResponse({"error": "invalid uuid"}, status_code=400)

    item_result = await db.execute(
        select(ContentItem).where(ContentItem.id == uid)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        return JSONResponse({"error": "not found"}, status_code=404)

    insight_result = await db.execute(
        select(ContentInsight).where(ContentInsight.content_item_id == uid)
    )
    insight = insight_result.scalar_one_or_none()

    # Fetch any generated posts for this item belonging to the current user
    posts_result = await db.execute(
        select(GeneratedPost).where(
            and_(
                GeneratedPost.content_item_id == uid,
                GeneratedPost.user_id == current_user.id,
            )
        ).order_by(GeneratedPost.created_at.desc())
    )
    posts = posts_result.scalars().all()

    generated_posts = {
        p.platform: {
            "id": str(p.id),
            "hook": p.hook,
            "caption": p.caption,
            "hashtags": p.hashtags or [],
            "call_to_action": p.call_to_action,
            "script_outline": p.script_outline,
            "thread_tweets": p.thread_tweets or [],
            "engagement_tips": p.engagement_tips or [],
            "created_at": p.created_at.isoformat(),
        }
        for p in posts
    }

    return JSONResponse({
        **_item_with_insight(item, insight),
        "generated_posts": generated_posts,
    })


@router.get("/runs")
async def get_pipeline_runs(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """Pipeline run history — for the dashboard health panel."""
    result = await db.execute(
        select(AgentRun)
        .order_by(desc(AgentRun.started_at))
        .limit(limit)
        .offset(offset)
    )
    runs = result.scalars().all()

    count_result = await db.execute(select(func.count(AgentRun.id)))
    total = count_result.scalar() or 0

    # Quick health summary
    last_success = None
    last_run = runs[0] if runs else None
    if last_run and last_run.status == AgentStatus.SUCCESS:
        last_success = last_run.started_at.isoformat()

    return JSONResponse({
        "runs": [_run_to_dict(r) for r in runs],
        "total": total,
        "last_run_status": last_run.status.value if last_run else None,
        "last_success_at": last_success,
    })


@router.get("/runs/{run_id}")
async def get_run_detail(
    run_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """Full detail for one pipeline run."""
    try:
        uid = uuid.UUID(run_id)
    except ValueError:
        return JSONResponse({"error": "invalid uuid"}, status_code=400)

    result = await db.execute(select(AgentRun).where(AgentRun.id == uid))
    run = result.scalar_one_or_none()
    if not run:
        return JSONResponse({"error": "not found"}, status_code=404)

    return JSONResponse(_run_to_dict(run))


@router.get("/stats")
async def get_insight_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """
    Aggregate stats for the dashboard header card.
    Returns counts for last 24 h and 7 d windows.
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d  = now - timedelta(days=7)

    # Items with insights in last 24 h
    analysed_24h = (await db.execute(
        select(func.count(ContentInsight.id))
        .join(ContentItem, ContentInsight.content_item_id == ContentItem.id)
        .where(ContentItem.fetched_at >= cutoff_24h)
    )).scalar() or 0

    # Value gap picks in last 24 h
    gap_24h = (await db.execute(
        select(func.count(ContentInsight.id))
        .join(ContentItem, ContentInsight.content_item_id == ContentItem.id)
        .where(
            and_(
                ContentItem.fetched_at >= cutoff_24h,
                ContentInsight.is_value_gap == True,
            )
        )
    )).scalar() or 0

    # Fact-check failures in last 24 h (flag for creator to review)
    fact_failures_24h = (await db.execute(
        select(func.count(ContentInsight.id))
        .join(ContentItem, ContentInsight.content_item_id == ContentItem.id)
        .where(
            and_(
                ContentItem.fetched_at >= cutoff_24h,
                ContentInsight.fact_check_passed == False,
            )
        )
    )).scalar() or 0

    # Auto-generated posts in last 7 d
    auto_generated_7d = (await db.execute(
        select(func.count(GeneratedPost.id))
        .where(
            and_(
                GeneratedPost.user_id == current_user.id,
                GeneratedPost.created_at >= cutoff_7d,
            )
        )
    )).scalar() or 0

    # Last pipeline run
    last_run_result = await db.execute(
        select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()

    # Average virality of last 24 h items that have insights
    avg_virality_result = await db.execute(
        select(func.avg(ContentInsight.virality_score))
        .join(ContentItem, ContentInsight.content_item_id == ContentItem.id)
        .where(ContentItem.fetched_at >= cutoff_24h)
    )
    avg_virality = avg_virality_result.scalar()

    return JSONResponse({
        "analysed_items_24h":    analysed_24h,
        "value_gap_picks_24h":   gap_24h,
        "fact_check_flags_24h":  fact_failures_24h,
        "auto_generated_posts_7d": auto_generated_7d,
        "avg_virality_24h":      round(float(avg_virality), 4) if avg_virality else 0.0,
        "last_pipeline_run": _run_to_dict(last_run) if last_run else None,
    })
