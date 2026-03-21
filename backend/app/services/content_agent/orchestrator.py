"""
Master Orchestrator — coordinates the full multi-agent pipeline.

Pipeline stages (run sequentially; each stage failure is isolated):

  Stage 0 — Scout       : collector.collect_all()  — fetch raw items from all sources
  Stage 1 — Score       : agent.score_items() + agent.summarise_item()  — existing scorer
  Stage 2 — Analyst     : analyst_agent.run_analyst_pass()  — virality, gap, B-Roll
  Stage 3 — FactChecker : fact_checker.run_fact_checker_pass()  — claim verification
  Stage 4 — Creative    : creative_agent.run_creative_pass()  — platform content
  Stage 5 — Persist     : write ContentInsight + GeneratedPost rows; update AgentRun

Design principles:
  - Every stage wraps its own try/except.  A stage failure downgrades the
    run to PARTIAL and records the error, but the pipeline continues.
  - All DB I/O is centralised here; agents are pure functions.
  - AgentRun is created at start and committed at each stage so progress is
    visible even if the worker crashes mid-run.
  - Duplicate-safe: ContentInsight uses upsert (delete-then-insert)
    because it has a unique constraint on content_item_id.
  - GeneratedPost creation reuses the existing logic from agent.py endpoint
    so the dashboard sees results from both manual and automated generation.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

PLATFORMS = ["twitter_thread", "linkedin", "instagram", "youtube_script"]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _elapsed(start: float) -> float:
    return round(time.monotonic() - start, 2)


async def _upsert_insight(
    db,
    content_item_id: uuid.UUID,
    item: dict[str, Any],
) -> None:
    """Delete-then-insert content insight (SQLAlchemy has no cross-DB upsert)."""
    from sqlalchemy import delete
    from app.models.models import ContentInsight

    await db.execute(
        delete(ContentInsight).where(
            ContentInsight.content_item_id == content_item_id
        )
    )
    insight = ContentInsight(
        content_item_id=content_item_id,
        virality_score=float(item.get("virality_score", 0.0)),
        cross_source_count=int(item.get("cross_source_count", 1)),
        trend_velocity=float(item.get("trend_velocity", 0.0)),
        sentiment_breakdown=item.get("sentiment_breakdown"),
        is_value_gap=bool(item.get("is_value_gap", False)),
        gap_explanation=item.get("gap_explanation") or None,
        suggested_angle=item.get("suggested_angle") or None,
        broll_assets=item.get("broll_assets") or None,
        fact_check_passed=item.get("fact_check_passed"),
        fact_check_confidence=item.get("fact_check_confidence"),
        flagged_claims=item.get("flagged_claims") or None,
        computed_at=_now(),
    )
    db.add(insight)


async def _persist_generated_post(
    db,
    content_item_id: uuid.UUID,
    platform: str,
    content: dict[str, Any],
    user_id: uuid.UUID | None = None,
) -> None:
    """
    Persist a GeneratedPost from the orchestrator's creative pass.

    The orchestrator runs without a user context so we use a sentinel
    user_id (the dev user in dev; None is rejected by the FK, so we
    skip persistence if no user_id is resolvable).
    """
    from sqlalchemy import select, and_
    from app.models.models import GeneratedPost
    from app.services.content_agent.hashtags import get_hashtags, format_hashtags

    if user_id is None:
        return  # no user context — skip; content still visible via /insights API

    existing = await db.execute(
        select(GeneratedPost).where(
            and_(
                GeneratedPost.content_item_id == content_item_id,
                GeneratedPost.user_id == user_id,
                GeneratedPost.platform == platform,
            )
        )
    )
    if existing.scalar_one_or_none():
        return  # already exists from manual generation; don't overwrite

    # Merge AI hashtags with curated set
    ai_hashtags = content.get("hashtags") or []
    curated = get_hashtags("other", platform.replace("_thread", "").replace("_script", ""), count=10)
    merged = list(dict.fromkeys(ai_hashtags + curated))[:20]

    post = GeneratedPost(
        content_item_id=content_item_id,
        user_id=user_id,
        platform=platform,
        hook=content.get("hook", ""),
        caption=content.get("caption", ""),
        hashtags=format_hashtags(merged),
        call_to_action=content.get("call_to_action", ""),
        script_outline=content.get("script_outline", ""),
        thread_tweets=content.get("thread_tweets", []),
        engagement_tips=content.get("engagement_tips", []),
    )
    db.add(post)


async def _get_recent_coverage_categories(db) -> list[str]:
    """Return list of category values from GeneratedPost × ContentItem for last 30 days."""
    from sqlalchemy import select, and_
    from datetime import timedelta
    from app.models.models import GeneratedPost, ContentItem

    cutoff = _now() - timedelta(days=30)
    result = await db.execute(
        select(ContentItem.category)
        .join(GeneratedPost, GeneratedPost.content_item_id == ContentItem.id)
        .where(GeneratedPost.created_at >= cutoff)
        .limit(100)
    )
    return [str(row[0]) for row in result.all()]


async def _get_any_active_user_id(db) -> uuid.UUID | None:
    """
    Return the first active user's ID for automated content generation.
    In a multi-user system, orchestrator-generated content is associated
    with the admin/first user.  This is intentional — creators can then
    see and edit the pre-generated content.
    """
    from sqlalchemy import select
    from app.models.models import User

    result = await db.execute(
        select(User.id).where(User.is_active == True).limit(1)
    )
    row = result.scalar_one_or_none()
    return uuid.UUID(str(row)) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

async def run_orchestrated_pipeline(
    *,
    triggered_by: str = "celery_beat",
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
    youtube_api_key: str = "",
    skip_creative: bool = False,
) -> dict[str, Any]:
    """
    Run the full multi-agent pipeline and return a summary dict.

    Errors in individual stages are recorded but do not abort the run.
    The returned dict is structured for Celery task result storage.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.models import AgentRun, AgentStatus, ContentItem, ContentCategory
    from sqlalchemy import select, update

    stage_errors: list[dict] = []
    run_id = uuid.uuid4()
    summary: dict[str, Any] = {
        "run_id": str(run_id),
        "triggered_by": triggered_by,
        "items_fetched": 0,
        "items_new": 0,
        "items_scored": 0,
        "items_fact_checked": 0,
        "items_generated": 0,
        "gap_signals_found": 0,
        "stage_errors": stage_errors,
    }

    # ── Create AgentRun record ────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        agent_run = AgentRun(
            id=run_id,
            triggered_by=triggered_by,
            status=AgentStatus.RUNNING,
            started_at=_now(),
        )
        db.add(agent_run)
        await db.commit()

    logger.info("orchestrator_start", run_id=str(run_id), triggered_by=triggered_by)

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 0: Scout — collect raw items
    # ─────────────────────────────────────────────────────────────────────────
    scout_start = time.monotonic()
    scout_duration: float | None = None
    try:
        from app.services.content_agent.collector import collect_all
        collect_stats = await collect_all(youtube_api_key=youtube_api_key)
        summary["items_fetched"] = collect_stats.get("fetched", 0)
        summary["items_new"] = collect_stats.get("new", 0)
        scout_duration = _elapsed(scout_start)
        logger.info("stage_scout_complete", **collect_stats)
    except Exception as exc:
        scout_duration = _elapsed(scout_start)
        stage_errors.append({"stage": "scout", "error": str(exc)})
        logger.error("stage_scout_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 1: Score + Summarise (existing agent pipeline)
    # ─────────────────────────────────────────────────────────────────────────
    analyst_start = time.monotonic()
    analyst_duration: float | None = None
    scored_items: list[dict] = []

    try:
        from app.services.content_agent.agent import score_items, summarise_item
        from app.models.models import ContentCategory as CC

        BATCH_SIZE = 10
        MIN_SCORE = 0.30  # Low threshold: default 0.5 always passes
        MAX_TO_PROCESS = 40

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ContentItem)
                .where(ContentItem.is_processed == False)
                .order_by(ContentItem.fetched_at.desc())
                .limit(MAX_TO_PROCESS)
            )
            raw_items = result.scalars().all()

        item_dicts = [
            {
                "id": str(item.id),
                "title": item.title,
                "raw_content": item.raw_content or "",
                "source_key": item.source_key,
                "source_label": item.source_label,
                "source_url": item.source_url or "",
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "relevance_score": 0.0,
                "category": "other",
                "summary": "",
                "key_points": [],
            }
            for item in raw_items
        ]

        # Batch scoring (gracefully handles no LLM — assigns 0.5 default)
        for i in range(0, len(item_dicts), BATCH_SIZE):
            batch = item_dicts[i : i + BATCH_SIZE]
            await score_items(batch, gemini_key=gemini_key, openai_key=openai_key)

        # Summarise ALL items (creates fallback from raw_content when no LLM)
        for item in item_dicts:
            await summarise_item(item, gemini_key=gemini_key, openai_key=openai_key)

        # Write scores + summaries back to ContentItem
        async with AsyncSessionLocal() as db:
            for item_dict in item_dicts:
                try:
                    cat_value = item_dict.get("category", "other")
                    try:
                        cat = CC(cat_value)
                    except ValueError:
                        cat = CC.OTHER
                    await db.execute(
                        update(ContentItem)
                        .where(ContentItem.id == uuid.UUID(item_dict["id"]))
                        .values(
                            relevance_score=item_dict.get("relevance_score", 0.0),
                            category=cat,
                            summary=item_dict.get("summary") or None,
                            key_points=item_dict.get("key_points") or None,
                            is_processed=True,
                            is_trending=item_dict.get("relevance_score", 0.0) >= 0.8,
                        )
                    )
                except Exception as inner_exc:
                    logger.warning("score_write_failed", error=str(inner_exc))
            await db.commit()

        # ALL processed items pass to analyst (pure-math virality works without LLM)
        scored_items = [x for x in item_dicts if x["relevance_score"] >= MIN_SCORE]
        summary["items_scored"] = len(scored_items)
        logger.info("stage_score_complete", total=len(item_dicts), scored=len(scored_items))

    except Exception as exc:
        stage_errors.append({"stage": "score", "error": str(exc)})
        logger.error("stage_score_failed", error=str(exc))

    analyst_duration = _elapsed(analyst_start)

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 2: Analyst — virality, trend velocity, value gap, B-Roll
    # ─────────────────────────────────────────────────────────────────────────
    analyst_intel_start = time.monotonic()
    analyst_intel_duration: float | None = None

    if scored_items:
        try:
            from app.services.content_agent.analyst_agent import run_analyst_pass

            async with AsyncSessionLocal() as db:
                recent_categories = await _get_recent_coverage_categories(db)

            scored_items = await run_analyst_pass(
                scored_items,
                recent_categories,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
                openai_key=openai_key,
            )
            gap_count = sum(1 for i in scored_items if i.get("is_value_gap"))
            summary["gap_signals_found"] = gap_count
            logger.info("stage_analyst_complete", gap_signals=gap_count)

        except Exception as exc:
            stage_errors.append({"stage": "analyst", "error": str(exc)})
            logger.error("stage_analyst_failed", error=str(exc))

    analyst_intel_duration = _elapsed(analyst_intel_start)

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 3: Fact Checker
    # ─────────────────────────────────────────────────────────────────────────
    checker_start = time.monotonic()
    checker_duration: float | None = None

    if scored_items:
        try:
            from app.services.content_agent.fact_checker import run_fact_checker_pass

            scored_items = await run_fact_checker_pass(
                scored_items,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
                openai_key=openai_key,
            )
            checked = sum(
                1 for i in scored_items if i.get("fact_check_passed") is not None
            )
            summary["items_fact_checked"] = checked
            logger.info("stage_factcheck_complete", checked=checked)

        except Exception as exc:
            stage_errors.append({"stage": "fact_checker", "error": str(exc)})
            logger.error("stage_factcheck_failed", error=str(exc))

    checker_duration = _elapsed(checker_start)

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 4: Persist ContentInsight rows
    # ─────────────────────────────────────────────────────────────────────────
    if scored_items:
        try:
            async with AsyncSessionLocal() as db:
                for item in scored_items:
                    try:
                        await _upsert_insight(db, uuid.UUID(item["id"]), item)
                    except Exception as inner_exc:
                        logger.warning(
                            "insight_persist_failed",
                            item_id=item.get("id"),
                            error=str(inner_exc),
                        )
                await db.commit()
            logger.info("stage_insight_persist_complete", count=len(scored_items))
        except Exception as exc:
            stage_errors.append({"stage": "insight_persist", "error": str(exc)})
            logger.error("stage_insight_persist_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 5: Creative Agent — generate platform content
    # ─────────────────────────────────────────────────────────────────────────
    creative_start = time.monotonic()
    creative_duration: float | None = None

    if scored_items and not skip_creative:
        try:
            from app.services.content_agent.creative_agent import run_creative_pass

            creative_results = await run_creative_pass(
                scored_items,
                platforms=PLATFORMS,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
                openai_key=openai_key,
            )

            # Persist generated posts
            async with AsyncSessionLocal() as db:
                user_id = await _get_any_active_user_id(db)
                generated_count = 0
                for item_id_str, platform_contents in creative_results.items():
                    for platform, content in platform_contents.items():
                        try:
                            await _persist_generated_post(
                                db,
                                uuid.UUID(item_id_str),
                                platform,
                                content,
                                user_id=user_id,
                            )
                            generated_count += 1
                        except Exception as inner_exc:
                            logger.warning(
                                "creative_persist_failed",
                                item_id=item_id_str,
                                platform=platform,
                                error=str(inner_exc),
                            )
                await db.commit()

            summary["items_generated"] = generated_count
            logger.info("stage_creative_complete", generated=generated_count)

        except Exception as exc:
            stage_errors.append({"stage": "creative", "error": str(exc)})
            logger.error("stage_creative_failed", error=str(exc))

    creative_duration = _elapsed(creative_start)

    # ─────────────────────────────────────────────────────────────────────────
    # Finalise AgentRun
    # ─────────────────────────────────────────────────────────────────────────
    final_status = (
        AgentStatus.FAILED
        if len(stage_errors) >= 4  # all stages failed
        else AgentStatus.PARTIAL
        if stage_errors
        else AgentStatus.SUCCESS
    )
    summary["status"] = final_status.value
    summary["stage_errors"] = stage_errors

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(AgentRun)
                .where(AgentRun.id == run_id)
                .values(
                    status=final_status,
                    scout_duration_s=scout_duration,
                    # analyst_duration_s covers both score + analyst intel
                    analyst_duration_s=round(
                        (analyst_duration or 0) + (analyst_intel_duration or 0), 2
                    ),
                    checker_duration_s=checker_duration,
                    creative_duration_s=creative_duration,
                    items_fetched=summary["items_fetched"],
                    items_new=summary["items_new"],
                    items_scored=summary["items_scored"],
                    items_fact_checked=summary["items_fact_checked"],
                    items_generated=summary["items_generated"],
                    gap_signals_found=summary["gap_signals_found"],
                    stage_errors=stage_errors if stage_errors else None,
                    finished_at=_now(),
                )
            )
            await db.commit()
    except Exception as exc:
        logger.error("agent_run_finalise_failed", error=str(exc))

    logger.info(
        "orchestrator_complete",
        run_id=str(run_id),
        pipeline_status=final_status.value,
        **{k: v for k, v in summary.items() if k not in ("stage_errors", "run_id", "triggered_by", "status")},
    )
    return summary
