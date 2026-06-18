"""Celery tasks — workspace-aware content agent pipeline + publishing.

v2 changes:
  - run_content_agent now requires workspace_id (deserialized into RunContext)
  - Schedule-triggered runs iterate over active workspaces
  - distribute_post updated for future PublishJob integration
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import structlog

from app.workers.celery_app import celery_app
from app.constants import CELERY_MAX_RETRIES, CELERY_RETRY_BACKOFF_S

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.run_content_agent",
    bind=True,
    max_retries=2,
    soft_time_limit=1800,
    time_limit=2100,
)
def run_content_agent(
    self,
    workspace_id: str | None = None,
    actor_id: str = "system",
    trigger: str = "schedule",
    skip_creative: bool = False,
) -> dict:
    """Multi-agent orchestrated pipeline: Scout→Score→Analyst→FactCheck→Creative.

    Can be invoked three ways:
      1. celery beat (no workspace_id → runs for ALL active workspaces)
      2. manual API trigger (workspace_id provided)
      3. webhook replay (workspace_id + trigger="webhook")
    """
    try:
        if workspace_id:
            return asyncio.run(
                _run_for_workspace(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    trigger=trigger,
                    skip_creative=skip_creative,
                )
            )
        else:
            return asyncio.run(
                _run_for_all_workspaces(
                    trigger=trigger,
                    skip_creative=skip_creative,
                )
            )
    except Exception as exc:
        logger.error("run_content_agent_task_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _run_for_workspace(
    *,
    workspace_id: str,
    actor_id: str,
    trigger: str,
    skip_creative: bool,
) -> dict:
    from app.runtime.context import RunContext
    from app.services.content_agent.orchestrator import run_orchestrated_pipeline

    ctx = RunContext(
        workspace_id=uuid.UUID(workspace_id),
        actor_id=actor_id,
        trigger=trigger,
    )
    return await run_orchestrated_pipeline(ctx=ctx, skip_creative=skip_creative)


async def _run_for_all_workspaces(
    *,
    trigger: str,
    skip_creative: bool,
) -> dict:
    """Run pipeline for every active workspace that has completed onboarding."""
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Workspace
    from app.runtime.context import RunContext
    from app.services.content_agent.orchestrator import run_orchestrated_pipeline
    from sqlalchemy import select

    results = {}

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workspace.id).where(
                Workspace.onboarding_completed == True,
                Workspace.deleted_at.is_(None),
            )
        )
        workspace_ids = [row[0] for row in result.all()]

    logger.info("batch_pipeline_start", workspace_count=len(workspace_ids))

    for ws_id in workspace_ids:
        try:
            ctx = RunContext.schedule_context(ws_id)
            summary = await run_orchestrated_pipeline(ctx=ctx, skip_creative=skip_creative)
            results[str(ws_id)] = summary.get("status", "unknown")
        except Exception as exc:
            results[str(ws_id)] = f"error:{type(exc).__name__}"
            logger.error("workspace_pipeline_failed", workspace_id=str(ws_id), error=str(exc))

    logger.info("batch_pipeline_complete", results=results)
    return {"workspaces_processed": len(workspace_ids), "results": results}


# ─────────────────────────────────────────────────────────────────────────────
# Post distribution (legacy — kept for backward compat)
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.tasks.distribute_post",
    max_retries=CELERY_MAX_RETRIES,
    default_retry_delay=CELERY_RETRY_BACKOFF_S,
    acks_late=True,
)
def distribute_post(self, post_id: str) -> dict:
    return asyncio.run(_distribute(self, post_id))


async def _distribute(task, post_id: str) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.models.models import User
    from app.services.auth_service import AuthService
    from app.services.cache_service import get_cache_instance
    from app.config import get_settings
    from app.repositories.repositories import UserRepository
    from sqlalchemy import select as sa_select

    settings = get_settings()
    cache = get_cache_instance()

    # NOTE: This distribute_post task is legacy. Future publishing uses PublishJob.
    # Keeping for backward compatibility with existing scheduled posts.
    logger.warning("legacy_distribute_post_called", post_id=post_id)
    return {"status": "legacy_skipped", "post_id": post_id}


# ─────────────────────────────────────────────────────────────────────────────
# Publish Job processor (new v2 pattern)
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.process_publish_jobs",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=660,
)
def process_publish_jobs(self) -> dict:
    """Process all queued publish jobs that are due."""
    return asyncio.run(_process_publish_jobs())


async def _process_publish_jobs() -> dict:
    """Find and execute queued publish jobs via platform adapters."""
    from app.db.session import AsyncSessionLocal
    from app.services.publish_executor import process_due_jobs

    async with AsyncSessionLocal() as db:
        return await process_due_jobs(db)


async def _notify_user(cache, user_id: str, success: int, failed: int) -> None:
    sub = await cache.get_push_subscription(user_id)
    if not sub:
        return
    try:
        from pywebpush import webpush
        from app.config import get_settings
        import json

        s = get_settings()
        if not s.VAPID_PRIVATE_KEY:
            return
        title = "✅ Published!" if failed == 0 else "⚠️ Partial publish"
        body = f"Posted to {success} platform(s)" if failed == 0 else f"{success} succeeded, {failed} failed"
        webpush(
            subscription_info=sub,
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=s.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{s.VAPID_EMAIL}"},
        )
    except Exception as exc:
        logger.warning("push_failed", user_id=user_id, error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Outbox processor — durable async event delivery
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.process_outbox",
    bind=True,
    max_retries=1,
    soft_time_limit=120,
    time_limit=150,
)
def process_outbox(self) -> dict:
    """Process pending outbox events with retry/dead-letter support."""
    return asyncio.run(_process_outbox())


async def _process_outbox() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.outbox_service import OutboxService

    async with AsyncSessionLocal() as db:
        outbox = OutboxService(db)
        stats = await outbox.process_pending(batch_size=100)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Approval expiry — clean up stale pending approvals
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.expire_stale_approvals",
    bind=True,
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def expire_stale_approvals(self) -> dict:
    """Expire all pending approval requests past their expiry time."""
    return asyncio.run(_expire_stale_approvals())


async def _expire_stale_approvals() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.approval_service import ApprovalService

    async with AsyncSessionLocal() as db:
        svc = ApprovalService(db)
        count = await svc.expire_stale()
        await db.commit()
    return {"expired": count}


# ─────────────────────────────────────────────────────────────────────────────
# Goal check — daily nudge for all workspaces
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.check_goals",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def check_goals(self) -> dict:
    """Check goal progress for all active workspaces and emit nudges."""
    return asyncio.run(_check_goals_all_workspaces())


async def _check_goals_all_workspaces() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Workspace
    from app.services.content_agent.goal_agent import check_goals_for_workspace
    from sqlalchemy import select

    total_nudges = 0
    workspaces_checked = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workspace.id).where(
                Workspace.onboarding_completed == True,
                Workspace.deleted_at.is_(None),
            )
        )
        workspace_ids = [row[0] for row in result.all()]

    for ws_id in workspace_ids:
        try:
            async with AsyncSessionLocal() as db:
                nudges = await check_goals_for_workspace(db, ws_id)
                total_nudges += len(nudges)
                workspaces_checked += 1
        except Exception as exc:
            logger.error(
                "goal_check_failed",
                workspace_id=str(ws_id), error=str(exc),
            )

    logger.info(
        "goal_check_complete",
        workspaces=workspaces_checked, nudges=total_nudges,
    )
    return {"workspaces_checked": workspaces_checked, "nudges_sent": total_nudges}


# ─────────────────────────────────────────────────────────────────────────────
# Competitor monitoring — daily scrape + analysis
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.monitor_competitors",
    bind=True,
    max_retries=1,
    soft_time_limit=900,
    time_limit=960,
)
def monitor_competitors(self) -> dict:
    """Monitor competitors for all workspaces with competitor profiles."""
    return asyncio.run(_monitor_competitors_all_workspaces())


async def _monitor_competitors_all_workspaces() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.content_agent.competitor_agent import (
        monitor_competitors_for_workspace,
    )
    from app.domains.intelligence.models import CompetitorProfile
    from sqlalchemy import select, func

    total_observations = 0
    workspaces_processed = 0

    async with AsyncSessionLocal() as db:
        # Get distinct workspace_ids that have competitor profiles
        result = await db.execute(
            select(CompetitorProfile.workspace_id)
            .where(CompetitorProfile.is_active == True)
            .group_by(CompetitorProfile.workspace_id)
        )
        workspace_ids = [row[0] for row in result.all()]

    for ws_id in workspace_ids:
        try:
            async with AsyncSessionLocal() as db:
                observations = await monitor_competitors_for_workspace(db, ws_id)
                total_observations += observations
                workspaces_processed += 1
        except Exception as exc:
            logger.error(
                "competitor_monitor_failed",
                workspace_id=str(ws_id), error=str(exc),
            )

    logger.info(
        "competitor_monitor_complete",
        workspaces=workspaces_processed,
        observations=total_observations,
    )
    return {
        "workspaces_processed": workspaces_processed,
        "observations": total_observations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Analytics sync — pull engagement metrics from connected platforms
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.sync_analytics",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=660,
)
def sync_analytics(self) -> dict:
    """Sync analytics for all workspaces with connected social accounts."""
    return asyncio.run(_sync_analytics_all())


async def _sync_analytics_all() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.analytics_sync import sync_all_workspaces

    async with AsyncSessionLocal() as db:
        return await sync_all_workspaces(db)


# ─────────────────────────────────────────────────────────────────────────────
# Token refresh — proactive refresh of expiring social account tokens
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.run_token_refresh",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def run_token_refresh(self) -> dict:
    """Refresh expiring social account tokens (within 24h window)."""
    return asyncio.run(_run_token_refresh())


async def _run_token_refresh() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.token_refresh_service import refresh_expiring_tokens

    async with AsyncSessionLocal() as db:
        return await refresh_expiring_tokens(db)


# ─────────────────────────────────────────────────────────────────────────────
# Business tasks — DM sync and AI evaluation
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.sync_all_inboxes",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=660,
)
def sync_all_inboxes(self) -> dict:
    """Sync DMs from platform APIs for all workspaces."""
    return asyncio.run(_sync_all_inboxes())


async def _sync_all_inboxes() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Workspace
    from app.runtime.context import RunContext
    from app.services.business.inbox_sync import sync_workspace_dms
    from sqlalchemy import select
    
    total_fetched = 0
    total_new = 0
    workspaces_processed = 0
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workspace.id).where(
                Workspace.onboarding_completed == True,
                Workspace.deleted_at.is_(None),
            )
        )
        workspace_ids = [row[0] for row in result.all()]
    
    for ws_id in workspace_ids:
        try:
            async with AsyncSessionLocal() as db:
                ctx = RunContext.schedule_context(ws_id)
                stats = await sync_workspace_dms(db, ctx)
                total_fetched += stats["fetched"]
                total_new += stats["new"]
                workspaces_processed += 1
        except Exception as exc:
            logger.error(
                "inbox_sync_failed",
                workspace_id=str(ws_id), error=str(exc),
            )
    
    logger.info(
        "inbox_sync_complete",
        workspaces=workspaces_processed,
        fetched=total_fetched,
        new=total_new,
    )
    return {
        "workspaces_processed": workspaces_processed,
        "fetched": total_fetched,
        "new": total_new,
    }


@celery_app.task(
    name="app.workers.tasks.evaluate_dms",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def evaluate_dms(self, workspace_id: str | None = None) -> dict:
    """Evaluate unread DMs with AI classification."""
    return asyncio.run(_evaluate_dms(workspace_id))


async def _evaluate_dms(workspace_id: str | None) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Workspace
    from app.runtime.context import RunContext
    from app.services.business.collab_evaluator import evaluate_unread_dms
    from sqlalchemy import select
    
    if workspace_id:
        # Evaluate for specific workspace
        async with AsyncSessionLocal() as db:
            ctx = RunContext.schedule_context(uuid.UUID(workspace_id))
            return await evaluate_unread_dms(db, ctx)
    else:
        # Evaluate for all workspaces
        total_evaluated = 0
        total_brand_deals = 0
        workspaces_processed = 0
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Workspace.id).where(
                    Workspace.onboarding_completed == True,
                    Workspace.deleted_at.is_(None),
                )
            )
            workspace_ids = [row[0] for row in result.all()]
        
        for ws_id in workspace_ids:
            try:
                async with AsyncSessionLocal() as db:
                    ctx = RunContext.schedule_context(ws_id)
                    stats = await evaluate_unread_dms(db, ctx)
                    total_evaluated += stats["evaluated"]
                    total_brand_deals += stats["brand_deals"]
                    workspaces_processed += 1
            except Exception as exc:
                logger.error(
                    "dm_evaluation_failed",
                    workspace_id=str(ws_id), error=str(exc),
                )
        
        logger.info(
            "dm_evaluation_complete",
            workspaces=workspaces_processed,
            evaluated=total_evaluated,
            brand_deals=total_brand_deals,
        )
        return {
            "workspaces_processed": workspaces_processed,
            "evaluated": total_evaluated,
            "brand_deals": total_brand_deals,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10: Proactive Trend Engine
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.scan_niche_trends",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,
    time_limit=1860,
)
def scan_niche_trends(self) -> dict:
    """Scan trends for all active niches (runs every 4 hours)."""
    return asyncio.run(_scan_niche_trends())


async def _scan_niche_trends() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Niche
    from app.services.agents.trend_sensor import scan_niche_trends as scan_trends
    from sqlalchemy import select
    
    total_trends = 0
    total_new = 0
    total_spikes = 0
    niches_scanned = 0
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Niche.id).where(Niche.is_active == True)
        )
        niche_ids = [row[0] for row in result.all()]
    
    for niche_id in niche_ids:
        try:
            async with AsyncSessionLocal() as db:
                stats = await scan_trends(db, niche_id)
                total_trends += stats["trends_found"]
                total_new += stats["trends_new"]
                total_spikes += stats["spike_events"]
                niches_scanned += 1
        except Exception as exc:
            logger.error(
                "niche_trend_scan_failed",
                niche_id=str(niche_id), error=str(exc),
            )
    
    logger.info(
        "niche_trends_scanned",
        niches=niches_scanned,
        trends=total_trends,
        new=total_new,
        spikes=total_spikes,
    )
    return {
        "niches_scanned": niches_scanned,
        "trends_found": total_trends,
        "trends_new": total_new,
        "spike_events": total_spikes,
    }


@celery_app.task(
    name="app.workers.tasks.dispatch_trend_insights",
    bind=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=360,
)
def dispatch_trend_insights(self, trend_id: str) -> dict:
    """Generate workspace insights for a spiking trend."""
    return asyncio.run(_dispatch_trend_insights(trend_id))


async def _dispatch_trend_insights(trend_id: str) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.agents.synthesis_agent import synthesize_trend_insights
    
    async with AsyncSessionLocal() as db:
        return await synthesize_trend_insights(db, uuid.UUID(trend_id))


@celery_app.task(
    name="app.workers.tasks.send_expo_push",
    bind=True,
    max_retries=3,
    soft_time_limit=30,
    time_limit=60,
)
def send_expo_push(
    self,
    workspace_id: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> dict:
    """Send Expo push notification with retry logic."""
    return asyncio.run(_send_expo_push(workspace_id, title, body, data))


async def _send_expo_push(
    workspace_id: str,
    title: str,
    body: str,
    data: dict | None,
) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.notifications.push_service import send_push_notification
    
    async with AsyncSessionLocal() as db:
        return await send_push_notification(
            db,
            uuid.UUID(workspace_id),
            title,
            body,
            data,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Agent Orchestrator — runs all 14 agents for all workspaces
# ─────────────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.run_agent_orchestrator",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,
    time_limit=1860,
)
def run_agent_orchestrator(
    self,
    workspace_id: str | None = None,
    agent_types: list[str] | None = None,
) -> dict:
    """Run agent orchestrator for specified workspace or all workspaces.
    
    Args:
        workspace_id: Specific workspace to run agents for, or None for all
        agent_types: List of agent types to run, or None for all agents
    """
    return asyncio.run(_run_agent_orchestrator(workspace_id, agent_types))


async def _run_agent_orchestrator(
    workspace_id: str | None,
    agent_types: list[str] | None,
) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.domains.control.models import Workspace
    from app.runtime.context import RunContext
    from app.services.agents.orchestrator import run_agent_orchestrator as run_agents
    from sqlalchemy import select
    
    if workspace_id:
        # Run for specific workspace
        ctx = RunContext.schedule_context(uuid.UUID(workspace_id))
        return await run_agents(ctx, agent_types)
    else:
        # Run for all active workspaces
        results = {}
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Workspace.id).where(
                    Workspace.onboarding_completed == True,
                    Workspace.deleted_at.is_(None),
                )
            )
            workspace_ids = [row[0] for row in result.all()]
        
        for ws_id in workspace_ids:
            try:
                ctx = RunContext.schedule_context(ws_id)
                summary = await run_agents(ctx, agent_types)
                results[str(ws_id)] = summary.get("status", "unknown")
            except Exception as exc:
                results[str(ws_id)] = f"error:{type(exc).__name__}"
                logger.error("agent_orchestrator_failed", workspace_id=str(ws_id), error=str(exc))
        
        return {"workspaces_processed": len(workspace_ids), "results": results}