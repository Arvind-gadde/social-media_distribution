"""Master Orchestrator v2 — workspace-aware, RunContext-governed pipeline.

Pipeline stages (run sequentially; each stage failure is isolated):

  Stage 0 — Scout       : collector.collect_all()  — fetch raw items from all sources
  Stage 1 — Score       : agent.score_items() + agent.summarise_item()  — scoring + summaries
  Stage 2 — Analyst     : analyst_agent.run_analyst_pass()  — virality, gap, B-Roll
  Stage 3 — FactChecker : fact_checker.run_fact_checker_pass()  — claim verification
  Stage 4 — Creative    : creative_agent.run_creative_pass()  — platform content
  Stage 5 — Persist     : write SourceDocumentInsight + ContentVariant rows; update AgentRun

Key v2 changes:
  - RunContext is MANDATORY — no more _get_any_active_user_id()
  - All DB writes scoped to workspace_id
  - Uses SourceDocument (not ContentItem)
  - Uses SourceDocumentInsight (not ContentInsight)
  - Uses ContentProject + ContentVariant (not GeneratedPost)
  - Uses AgentStep for per-stage observability
  - Uses unified LLM provider for cost tracking
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.runtime.context import RunContext

logger = structlog.get_logger(__name__)

PLATFORMS = ["twitter", "linkedin", "instagram", "youtube"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _elapsed(start: float) -> float:
    return round(time.monotonic() - start, 2)


async def _record_step(
    db,
    agent_run_id: uuid.UUID,
    step_name: str,
    step_order: int,
    *,
    status: str = "running",
    provider: str | None = None,
    model: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    latency_ms: int = 0,
    error: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
) -> uuid.UUID:
    """Record an agent step for observability."""
    from app.domains.intelligence.models import AgentStep

    step = AgentStep(
        agent_run_id=agent_run_id,
        step_name=step_name,
        step_order=step_order,
        status=status,
        provider=provider,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        error=error,
        input_summary=input_summary,
        output_summary=output_summary,
    )
    db.add(step)
    await db.flush()
    return step.id


async def _upsert_insight(
    db,
    source_doc_id: uuid.UUID,
    item: dict[str, Any],
) -> None:
    """Delete-then-insert source document insight."""
    from sqlalchemy import delete
    from app.domains.intelligence.models import SourceDocumentInsight

    await db.execute(
        delete(SourceDocumentInsight).where(
            SourceDocumentInsight.source_document_id == source_doc_id
        )
    )
    insight = SourceDocumentInsight(
        source_document_id=source_doc_id,
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


async def _persist_variant(
    db,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    source_doc_id: uuid.UUID | None,
    platform: str,
    content: dict[str, Any],
) -> None:
    """Persist a ContentVariant from the creative pass."""
    from app.domains.execution.models import ContentVariant, AuthoringSource
    from app.services.content_agent.hashtags import get_hashtags, format_hashtags

    # Merge AI hashtags with curated set
    ai_hashtags = content.get("hashtags") or []
    clean_platform = platform.replace("_thread", "").replace("_script", "")
    curated = get_hashtags("other", clean_platform, count=10)
    merged = list(dict.fromkeys(ai_hashtags + curated))[:20]

    variant = ContentVariant(
        workspace_id=workspace_id,
        project_id=project_id,
        source_document_id=source_doc_id,
        target_platform=platform,
        hook=content.get("hook", ""),
        caption=content.get("caption", ""),
        hashtags=merged,
        call_to_action=content.get("call_to_action", ""),
        script_outline=content.get("script_outline", ""),
        thread_tweets=content.get("thread_tweets", []),
        engagement_tips=content.get("engagement_tips", []),
        authoring_source=AuthoringSource.ASSISTANT,
        prompt_version="v2.0",
    )
    db.add(variant)


async def _create_project_for_item(
    db,
    workspace_id: uuid.UUID,
    item: dict[str, Any],
    actor_id: str,
) -> uuid.UUID:
    """Create a ContentProject from a scored source document."""
    from app.domains.execution.models import ContentProject, ProjectStatus

    actor_uuid = None
    try:
        actor_uuid = uuid.UUID(actor_id)
    except ValueError:
        pass

    project = ContentProject(
        workspace_id=workspace_id,
        title=item.get("title", "Untitled"),
        description=item.get("summary", ""),
        status=ProjectStatus.DRAFT,
        target_platforms=PLATFORMS,
        virality_score=item.get("virality_score"),
        ai_rationale=item.get("suggested_angle"),
        created_by=actor_uuid,
    )
    db.add(project)
    await db.flush()
    return project.id


async def _get_recent_coverage_categories(db, workspace_id: uuid.UUID) -> list[str]:
    """Return categories from recent content projects."""
    from sqlalchemy import select
    from datetime import timedelta
    from app.domains.execution.models import ContentVariant

    cutoff = _now() - timedelta(days=30)
    result = await db.execute(
        select(ContentVariant.target_platform)
        .where(
            ContentVariant.workspace_id == workspace_id,
            ContentVariant.created_at >= cutoff,
        )
        .limit(100)
    )
    return [str(row[0]) for row in result.all()]


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

async def run_orchestrated_pipeline(
    *,
    ctx: RunContext,
    skip_creative: bool = False,
) -> dict[str, Any]:
    """Run the full multi-agent pipeline under a RunContext.

    Args:
        ctx: Mandatory RunContext with workspace_id and actor_id.
        skip_creative: If True, skip the creative generation stage.

    Returns:
        Summary dict with pipeline results.
    """
    from app.db.session import AsyncSessionLocal
    from app.domains.intelligence.models import AgentRun, AgentRunStatus
    from app.domains.intelligence.models import SourceDocument
    from app.config import get_settings
    from sqlalchemy import select, update

    settings = get_settings()
    stage_errors: list[dict] = []
    run_id = uuid.uuid4()
    summary: dict[str, Any] = {
        "run_id": str(run_id),
        "workspace_id": str(ctx.workspace_id),
        "correlation_id": ctx.correlation_id,
        "trigger": ctx.trigger,
        "items_fetched": 0,
        "items_new": 0,
        "items_scored": 0,
        "items_fact_checked": 0,
        "items_generated": 0,
        "gap_signals_found": 0,
        "total_tokens_used": 0,
        "total_cost_usd": 0.0,
        "stage_errors": stage_errors,
    }

    log = logger.bind(**ctx.to_log_dict(), run_id=str(run_id))

    # ── Create AgentRun record ────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        agent_run = AgentRun(
            id=run_id,
            workspace_id=ctx.workspace_id,
            actor_id=ctx.actor_id,
            trigger=ctx.trigger,
            correlation_id=ctx.correlation_id,
            run_type="full_pipeline",
            status=AgentRunStatus.RUNNING,
            started_at=_now(),
        )
        db.add(agent_run)
        await db.commit()

    log.info("orchestrator_start")

    # ─────────────────────────────────────────────────────────────────────
    # Stage 0: Scout — collect raw items
    # ─────────────────────────────────────────────────────────────────────
    scout_start = time.monotonic()
    scout_duration: float | None = None
    try:
        from app.services.content_agent.collector import collect_all
        collect_stats = await collect_all(youtube_api_key=settings.YOUTUBE_API_KEY)
        summary["items_fetched"] = collect_stats.get("fetched", 0)
        summary["items_new"] = collect_stats.get("new", 0)
        scout_duration = _elapsed(scout_start)

        async with AsyncSessionLocal() as db:
            await _record_step(
                db, run_id, "scout", 0,
                status="completed",
                latency_ms=int(scout_duration * 1000),
                output_summary=f"Fetched {summary['items_fetched']}, new {summary['items_new']}",
            )
            await db.commit()

        log.info("stage_scout_complete", **collect_stats)
    except Exception as exc:
        scout_duration = _elapsed(scout_start)
        stage_errors.append({"stage": "scout", "error": str(exc)})
        async with AsyncSessionLocal() as db:
            await _record_step(
                db, run_id, "scout", 0, status="failed", error=str(exc),
            )
            await db.commit()
        log.error("stage_scout_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Stage 1: Score + Summarise
    # ─────────────────────────────────────────────────────────────────────
    analyst_start = time.monotonic()
    analyst_duration: float | None = None
    scored_items: list[dict] = []

    try:
        from app.services.content_agent.agent import score_items, summarise_item

        BATCH_SIZE = 10
        MIN_SCORE = 0.30
        MAX_TO_PROCESS = 40

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SourceDocument)
                .where(SourceDocument.is_processed == False)
                .order_by(SourceDocument.fetched_at.desc())
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

        for i in range(0, len(item_dicts), BATCH_SIZE):
            batch = item_dicts[i: i + BATCH_SIZE]
            await score_items(
                batch,
                gemini_key=settings.GEMINI_API_KEY,
                openai_key=settings.OPENAI_API_KEY,
            )

        for item in item_dicts:
            await summarise_item(
                item,
                gemini_key=settings.GEMINI_API_KEY,
                openai_key=settings.OPENAI_API_KEY,
            )

        # Write scores back to SourceDocument
        async with AsyncSessionLocal() as db:
            for item_dict in item_dicts:
                try:
                    cat_value = item_dict.get("category", "other")
                    await db.execute(
                        update(SourceDocument)
                        .where(SourceDocument.id == uuid.UUID(item_dict["id"]))
                        .values(
                            relevance_score=item_dict.get("relevance_score", 0.0),
                            category=cat_value,
                            summary=item_dict.get("summary") or None,
                            key_points=item_dict.get("key_points") or None,
                            is_processed=True,
                            is_trending=item_dict.get("relevance_score", 0.0) >= 0.8,
                        )
                    )
                except Exception as inner_exc:
                    log.warning("score_write_failed", error=str(inner_exc))
            await db.commit()

        scored_items = [x for x in item_dicts if x["relevance_score"] >= MIN_SCORE]
        summary["items_scored"] = len(scored_items)
        analyst_duration = _elapsed(analyst_start)

        async with AsyncSessionLocal() as db:
            await _record_step(
                db, run_id, "scorer", 1,
                status="completed",
                latency_ms=int(analyst_duration * 1000),
                output_summary=f"Scored {len(item_dicts)}, passed {len(scored_items)}",
            )
            await db.commit()

        log.info("stage_score_complete", total=len(item_dicts), scored=len(scored_items))

    except Exception as exc:
        analyst_duration = _elapsed(analyst_start)
        stage_errors.append({"stage": "score", "error": str(exc)})
        log.error("stage_score_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Stage 2: Analyst — virality, trend velocity, value gap, B-Roll
    # ─────────────────────────────────────────────────────────────────────
    analyst_intel_start = time.monotonic()
    analyst_intel_duration: float | None = None

    if scored_items:
        try:
            from app.services.content_agent.analyst_agent import run_analyst_pass

            async with AsyncSessionLocal() as db:
                recent_categories = await _get_recent_coverage_categories(db, ctx.workspace_id)

            scored_items = await run_analyst_pass(
                scored_items,
                recent_categories,
                anthropic_key=settings.ANTHROPIC_API_KEY,
                gemini_key=settings.GEMINI_API_KEY,
                openai_key=settings.OPENAI_API_KEY,
            )
            gap_count = sum(1 for i in scored_items if i.get("is_value_gap"))
            summary["gap_signals_found"] = gap_count
            analyst_intel_duration = _elapsed(analyst_intel_start)

            async with AsyncSessionLocal() as db:
                await _record_step(
                    db, run_id, "analyst", 2,
                    status="completed",
                    latency_ms=int(analyst_intel_duration * 1000),
                    output_summary=f"Gap signals: {gap_count}",
                )
                await db.commit()

            log.info("stage_analyst_complete", gap_signals=gap_count)

        except Exception as exc:
            analyst_intel_duration = _elapsed(analyst_intel_start)
            stage_errors.append({"stage": "analyst", "error": str(exc)})
            log.error("stage_analyst_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Stage 3: Fact Checker
    # ─────────────────────────────────────────────────────────────────────
    checker_start = time.monotonic()
    checker_duration: float | None = None

    if scored_items:
        try:
            from app.services.content_agent.fact_checker import run_fact_checker_pass
            scored_items = await run_fact_checker_pass(
                scored_items,
                anthropic_key=settings.ANTHROPIC_API_KEY,
                gemini_key=settings.GEMINI_API_KEY,
                openai_key=settings.OPENAI_API_KEY,
            )
            checked = sum(1 for i in scored_items if i.get("fact_check_passed") is not None)
            summary["items_fact_checked"] = checked
            checker_duration = _elapsed(checker_start)

            async with AsyncSessionLocal() as db:
                await _record_step(
                    db, run_id, "fact_checker", 3,
                    status="completed",
                    latency_ms=int(checker_duration * 1000),
                    output_summary=f"Checked {checked}",
                )
                await db.commit()

            log.info("stage_factcheck_complete", checked=checked)
        except Exception as exc:
            checker_duration = _elapsed(checker_start)
            stage_errors.append({"stage": "fact_checker", "error": str(exc)})
            log.error("stage_factcheck_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Stage 4: Persist SourceDocumentInsight rows
    # ─────────────────────────────────────────────────────────────────────
    if scored_items:
        try:
            async with AsyncSessionLocal() as db:
                for item in scored_items:
                    try:
                        await _upsert_insight(db, uuid.UUID(item["id"]), item)
                    except Exception as inner_exc:
                        log.warning("insight_persist_failed", item_id=item.get("id"), error=str(inner_exc))
                await db.commit()
            log.info("stage_insight_persist_complete", count=len(scored_items))
        except Exception as exc:
            stage_errors.append({"stage": "insight_persist", "error": str(exc)})
            log.error("stage_insight_persist_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Stage 5: Creative Agent — generate platform content
    # ─────────────────────────────────────────────────────────────────────
    creative_start = time.monotonic()
    creative_duration: float | None = None

    if scored_items and not skip_creative:
        try:
            from app.services.content_agent.creative_agent import run_creative_pass

            creative_results = await run_creative_pass(
                scored_items,
                platforms=PLATFORMS,
                anthropic_key=settings.ANTHROPIC_API_KEY,
                gemini_key=settings.GEMINI_API_KEY,
                openai_key=settings.OPENAI_API_KEY,
            )

            async with AsyncSessionLocal() as db:
                generated_count = 0
                for item_id_str, platform_contents in creative_results.items():
                    try:
                        project_id = await _create_project_for_item(
                            db, ctx.workspace_id,
                            next((i for i in scored_items if i["id"] == item_id_str), {}),
                            ctx.actor_id,
                        )
                        source_doc_id: uuid.UUID | None
                        try:
                            source_doc_id = uuid.UUID(item_id_str)
                        except ValueError:
                            source_doc_id = None

                        for platform, content in platform_contents.items():
                            try:
                                await _persist_variant(
                                    db, ctx.workspace_id, project_id,
                                    source_doc_id, platform, content,
                                )
                                generated_count += 1
                            except Exception as inner_exc:
                                log.warning(
                                    "creative_persist_failed",
                                    item_id=item_id_str, platform=platform,
                                    error=str(inner_exc),
                                )
                    except Exception as proj_exc:
                        log.warning("project_creation_failed", item_id=item_id_str, error=str(proj_exc))

                await db.commit()

            summary["items_generated"] = generated_count
            creative_duration = _elapsed(creative_start)

            async with AsyncSessionLocal() as db:
                await _record_step(
                    db, run_id, "creative", 5,
                    status="completed",
                    latency_ms=int(creative_duration * 1000),
                    output_summary=f"Generated {generated_count} variants",
                )
                await db.commit()

            log.info("stage_creative_complete", generated=generated_count)

        except Exception as exc:
            creative_duration = _elapsed(creative_start)
            stage_errors.append({"stage": "creative", "error": str(exc)})
            log.error("stage_creative_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────
    # Finalise AgentRun
    # ─────────────────────────────────────────────────────────────────────
    final_status = (
        AgentRunStatus.FAILED
        if len(stage_errors) >= 4
        else AgentRunStatus.PARTIAL
        if stage_errors
        else AgentRunStatus.SUCCESS
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
                    total_tokens_used=summary["total_tokens_used"],
                    total_cost_usd=summary["total_cost_usd"],
                    stage_errors=stage_errors if stage_errors else None,
                    finished_at=_now(),
                )
            )
            await db.commit()
    except Exception as exc:
        log.error("agent_run_finalise_failed", error=str(exc))

    log.info(
        "orchestrator_complete",
        pipeline_status=final_status.value,
        **{k: v for k, v in summary.items() if k not in ("stage_errors", "run_id", "triggered_by", "status", "workspace_id", "correlation_id", "trigger")},
    )
    return summary
