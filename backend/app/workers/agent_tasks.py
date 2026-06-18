"""Celery tasks for agent orchestration.

Phase 13: Agent Orchestration

Scheduled tasks for running agent workflows in the background.
"""
import uuid
import structlog
import asyncio
from celery import Task
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.db.session import get_async_session
from app.runtime.orchestration.workflow import run_agent_workflow
from app.runtime.correlation import set_correlation_id, generate_correlation_id

log = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED AGENT WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    queue="agents",
    name="agents.run_scheduled_workflow",
)
def run_scheduled_agent_workflow(
    self: Task,
    workspace_id: str,
    trigger: str = "schedule",
) -> dict:
    """Run agent workflow as a scheduled task.
    
    This task is triggered by Celery Beat on a schedule (e.g., hourly, daily).
    
    Args:
        workspace_id: Workspace UUID as string
        trigger: What triggered this run (default: "schedule")
    
    Returns:
        Final state dict with results
    
    Raises:
        Exception: If workflow execution fails after retries
    """
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    
    log.info("scheduled_agent_workflow.started",
             workspace_id=workspace_id,
             correlation_id=correlation_id,
             trigger=trigger)
    
    try:
        async def _run():
            async with get_async_session() as db:
                return await run_agent_workflow(
                    workspace_id=uuid.UUID(workspace_id),
                    actor_id="system",
                    trigger=trigger,
                    db=db,
                )
        
        final_state = asyncio.run(_run())
        
        log.info("scheduled_agent_workflow.completed",
                 workspace_id=workspace_id,
                 correlation_id=correlation_id,
                 insights_count=len(final_state["insights"]),
                 ideas_count=len(final_state["content_ideas"]),
                 agents_executed=len(final_state["active_agents"]))
        
        return {
            "status": "completed",
            "workspace_id": workspace_id,
            "insights_count": len(final_state["insights"]),
            "ideas_count": len(final_state["content_ideas"]),
            "agents_executed": final_state["active_agents"],
        }
        
    except Exception as exc:
        log.error("scheduled_agent_workflow.failed",
                  workspace_id=workspace_id,
                  correlation_id=correlation_id,
                  error=str(exc),
                  error_type=type(exc).__name__,
                  retry_count=self.request.retries)
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-SPECIFIC SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    max_retries=3,
    queue="agents",
    name="agents.run_trend_detection",
)
def run_trend_detection_task(
    self: Task,
    workspace_id: str,
) -> dict:
    """Run trend detection agent every 30 minutes.
    
    Args:
        workspace_id: Workspace UUID as string
    
    Returns:
        Agent result dict
    """
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    
    log.info("trend_detection_task.started",
             workspace_id=workspace_id,
             correlation_id=correlation_id)
    
    try:
        from app.runtime.orchestration.workflow import run_single_agent
        
        async def _run():
            async with get_async_session() as db:
                return await run_single_agent(
                    workspace_id=uuid.UUID(workspace_id),
                    actor_id="system",
                    agent_name="trend_detection",
                    db=db,
                )
        
        result_state = asyncio.run(_run())
        
        log.info("trend_detection_task.completed",
                 workspace_id=workspace_id,
                 insights_count=len(result_state["insights"]))
        
        return {
            "status": "completed",
            "agent": "trend_detection",
            "insights_count": len(result_state["insights"]),
        }
        
    except Exception as exc:
        log.error("trend_detection_task.failed",
                  workspace_id=workspace_id,
                  error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    queue="agents",
    name="agents.run_competitor_intelligence",
)
def run_competitor_intelligence_task(
    self: Task,
    workspace_id: str,
) -> dict:
    """Run competitor intelligence agent every 4 hours.
    
    Args:
        workspace_id: Workspace UUID as string
    
    Returns:
        Agent result dict
    """
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    
    log.info("competitor_intelligence_task.started",
             workspace_id=workspace_id,
             correlation_id=correlation_id)
    
    try:
        from app.runtime.orchestration.workflow import run_single_agent
        
        async def _run():
            async with get_async_session() as db:
                return await run_single_agent(
                    workspace_id=uuid.UUID(workspace_id),
                    actor_id="system",
                    agent_name="competitor_intelligence",
                    db=db,
                )
        
        result_state = asyncio.run(_run())
        
        log.info("competitor_intelligence_task.completed",
                 workspace_id=workspace_id,
                 insights_count=len(result_state["insights"]))
        
        return {
            "status": "completed",
            "agent": "competitor_intelligence",
            "insights_count": len(result_state["insights"]),
        }
        
    except Exception as exc:
        log.error("competitor_intelligence_task.failed",
                  workspace_id=workspace_id,
                  error=str(exc))
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(
    bind=True,
    max_retries=3,
    queue="agents",
    name="agents.run_news_research",
)
def run_news_research_task(
    self: Task,
    workspace_id: str,
) -> dict:
    """Run news & research agent every hour.
    
    Args:
        workspace_id: Workspace UUID as string
    
    Returns:
        Agent result dict
    """
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    
    log.info("news_research_task.started",
             workspace_id=workspace_id,
             correlation_id=correlation_id)
    
    try:
        from app.runtime.orchestration.workflow import run_single_agent
        
        async def _run():
            async with get_async_session() as db:
                return await run_single_agent(
                    workspace_id=uuid.UUID(workspace_id),
                    actor_id="system",
                    agent_name="news_research",
                    db=db,
                )
        
        result_state = asyncio.run(_run())
        
        log.info("news_research_task.completed",
                 workspace_id=workspace_id,
                 insights_count=len(result_state["insights"]))
        
        return {
            "status": "completed",
            "agent": "news_research",
            "insights_count": len(result_state["insights"]),
        }
        
    except Exception as exc:
        log.error("news_research_task.failed",
                  workspace_id=workspace_id,
                  error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    queue="agents",
    name="agents.run_goal_accountability",
)
def run_goal_accountability_task(
    self: Task,
    workspace_id: str,
) -> dict:
    """Run goal & accountability agent daily.
    
    Args:
        workspace_id: Workspace UUID as string
    
    Returns:
        Agent result dict
    """
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    
    log.info("goal_accountability_task.started",
             workspace_id=workspace_id,
             correlation_id=correlation_id)
    
    try:
        from app.runtime.orchestration.workflow import run_single_agent
        
        async def _run():
            async with get_async_session() as db:
                return await run_single_agent(
                    workspace_id=uuid.UUID(workspace_id),
                    actor_id="system",
                    agent_name="goal_accountability",
                    db=db,
                )
        
        result_state = asyncio.run(_run())
        
        log.info("goal_accountability_task.completed",
                 workspace_id=workspace_id,
                 insights_count=len(result_state["insights"]))
        
        return {
            "status": "completed",
            "agent": "goal_accountability",
            "insights_count": len(result_state["insights"]),
        }
        
    except Exception as exc:
        log.error("goal_accountability_task.failed",
                  workspace_id=workspace_id,
                  error=str(exc))
        raise self.retry(exc=exc, countdown=300)


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH WORKSPACE PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    queue="agents",
    name="agents.run_all_workspaces",
)
def run_all_workspaces_task(
    self: Task,
    agent_name: str | None = None,
) -> dict:
    """Run agent workflow for all active workspaces.
    
    This is the master task that Celery Beat calls on a schedule.
    It queries all active workspaces and spawns individual tasks for each.
    
    Args:
        agent_name: Optional specific agent to run (default: full workflow)
    
    Returns:
        Summary dict with task counts
    """
    log.info("run_all_workspaces.started", agent_name=agent_name)
    
    try:
        async def _get_workspaces():
            from sqlalchemy import select
            from app.domains.control.models import Workspace
            
            async with get_async_session() as db:
                result = await db.execute(
                    select(Workspace.id).where(
                        Workspace.deleted_at.is_(None),
                        # TODO: Add subscription tier check
                    )
                )
                return [str(row[0]) for row in result.all()]
        
        workspace_ids = asyncio.run(_get_workspaces())
        
        log.info("run_all_workspaces.found_workspaces",
                 count=len(workspace_ids))
        
        # Spawn individual tasks
        tasks_spawned = 0
        for workspace_id in workspace_ids:
            if agent_name:
                # Run specific agent
                if agent_name == "trend_detection":
                    run_trend_detection_task.delay(workspace_id)
                elif agent_name == "competitor_intelligence":
                    run_competitor_intelligence_task.delay(workspace_id)
                elif agent_name == "news_research":
                    run_news_research_task.delay(workspace_id)
                elif agent_name == "goal_accountability":
                    run_goal_accountability_task.delay(workspace_id)
                else:
                    log.warning("run_all_workspaces.unknown_agent",
                               agent_name=agent_name)
                    continue
            else:
                # Run full workflow
                run_scheduled_agent_workflow.delay(workspace_id)
            
            tasks_spawned += 1
        
        log.info("run_all_workspaces.completed",
                 workspaces_processed=len(workspace_ids),
                 tasks_spawned=tasks_spawned)
        
        return {
            "status": "completed",
            "workspaces_processed": len(workspace_ids),
            "tasks_spawned": tasks_spawned,
            "agent_name": agent_name,
        }
        
    except Exception as exc:
        log.error("run_all_workspaces.failed", error=str(exc))
        raise
