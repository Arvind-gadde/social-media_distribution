"""Agent Management API - Phase 15.

Exposes the 14-agent orchestration system through REST and WebSocket endpoints.
Follows AGENTS.md blueprint section 12 (API Design).
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
import structlog
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import BigInteger, case, select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import (
    Cache, CurrentUser, CurrentWorkspace, DbSession, WorkspaceCtx, require_workspace_role,
)
from app.config import get_settings
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.domains.control.models import WorkspaceMembership, InviteStatus
from app.domains.intelligence.models import (
    WorkspaceInsight, AgentRun, InsightType, AgentRunStatus,
)
from app.runtime.orchestration.workflow import run_agent_workflow, run_single_agent
from app.runtime.context import RunContext
from app.services.cache.cache_manager import CacheManager
from app.services.agent_event_bus import AgentEventSubscriber, publish_agent_event

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentConfigResponse(BaseModel):
    """Agent configuration for a workspace."""
    agent_type: str
    agent_name: str
    is_enabled: bool
    run_frequency: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    run_count: int
    success_count: int
    error_count: int
    success_rate: float


class AgentConfigUpdate(BaseModel):
    """Update agent configuration."""
    is_enabled: bool | None = None
    run_frequency: Literal["hourly", "every_6h", "daily", "weekly", "on_demand"] | None = None


class AgentTriggerRequest(BaseModel):
    """Trigger manual agent run."""
    agent_type: str | None = Field(None, description="Specific agent to run, or None for full workflow")
    budget_id: uuid.UUID | None = None


class AgentInsightResponse(BaseModel):
    """Workspace insight from agents."""
    id: uuid.UUID
    agent_type: str
    insight_type: str
    title: str
    body: str
    action_type: str | None
    action_data: dict | None
    priority: int
    niche_relevance_score: float
    is_read: bool
    is_dismissed: bool
    is_actioned: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentInsightUpdate(BaseModel):
    """Update insight status."""
    is_read: bool | None = None
    is_dismissed: bool | None = None
    is_actioned: bool | None = None


class AgentRunResponse(BaseModel):
    """Agent run execution details."""
    id: uuid.UUID
    workspace_id: uuid.UUID | None
    run_type: str
    status: str
    trigger: str
    correlation_id: str
    items_fetched: int
    items_new: int
    items_scored: int
    items_generated: int
    gap_signals_found: int
    total_tokens_used: int
    total_cost_usd: float
    stage_errors: list | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None

    model_config = {"from_attributes": True}

    @property
    def duration_seconds(self) -> float | None:
        if self.duration_ms is None:
            return None
        return self.duration_ms / 1000.0


class AgentStatusResponse(BaseModel):
    """Overall agent system status."""
    total_agents: int = 14
    enabled_agents: int
    last_run_at: datetime | None
    next_scheduled_run: datetime | None
    total_runs_today: int
    success_rate_today: float
    total_insights_unread: int
    total_insights_today: int


class PaginatedInsights(BaseModel):
    """Paginated insights response."""
    items: list[AgentInsightResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT CONFIGURATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=list[AgentConfigResponse])
async def list_agent_configs(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> list[AgentConfigResponse]:
    """List all agent configurations for the workspace.
    
    Returns configuration for all 14 agents including:
    - Enable/disable status
    - Run frequency
    - Last run time
    - Success metrics
    """
    # Define all 14 agents from AGENTS.md
    agent_types = [
        ("niche_intelligence", "Niche Intelligence Agent"),
        ("trend_detection", "Trend Detection Agent"),
        ("analytics_intelligence", "Analytics Intelligence Agent"),
        ("competitor_intelligence", "Competitor Intelligence Agent"),
        ("content_ideation", "Content Research & Ideation Agent"),
        ("goal_accountability", "Goal & Accountability Agent"),
        ("collaboration_business", "Collaboration & Business Agent"),
        ("news_research", "News & Research Agent"),
        ("tips_tricks", "Tips, Tricks & Platform Algorithm Agent"),
        ("smart_scheduling", "Smart Scheduling Agent"),
        ("growth_optimization", "Growth & Engagement Optimization Agent"),
        ("video_intelligence", "Video Intelligence Agent"),
        ("predictive_virality", "Predictive Virality Agent"),
        ("orchestrator", "Agent Orchestrator (Master)"),
    ]
    
    # Get run statistics for each agent
    configs = []
    for agent_type, agent_name in agent_types:
        # Get last run
        result = await db.execute(
            select(AgentRun)
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.run_type.contains(agent_type),
            )
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        last_run = result.scalar_one_or_none()
        
        # Get success/error counts
        result = await db.execute(
            select(
                func.count(AgentRun.id).label("total"),
                func.sum(
                    case((AgentRun.status == AgentRunStatus.SUCCESS, 1), else_=0)
                ).label("success"),
            )
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.run_type.contains(agent_type),
            )
        )
        stats = result.one()
        
        run_count = stats.total or 0
        success_count = stats.success or 0
        error_count = run_count - success_count
        success_rate = (success_count / run_count * 100) if run_count > 0 else 0.0
        
        configs.append(AgentConfigResponse(
            agent_type=agent_type,
            agent_name=agent_name,
            is_enabled=True,  # TODO: Add agent_configs table for per-workspace settings
            run_frequency="hourly",  # TODO: Make configurable
            last_run_at=last_run.started_at if last_run else None,
            next_run_at=None,  # TODO: Calculate from schedule
            run_count=run_count,
            success_count=success_count,
            error_count=error_count,
            success_rate=round(success_rate, 1),
        ))
    
    return configs


@router.patch("/{agent_type}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_type: str,
    body: AgentConfigUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> AgentConfigResponse:
    """Update agent configuration (enable/disable, frequency).
    
    Args:
        agent_type: Agent identifier (e.g., "trend_detection")
        body: Configuration updates
    
    Returns:
        Updated agent configuration
    """
    # TODO: Implement agent_configs table for per-workspace settings
    # For now, return mock response
    log.info("agent_config.update",
             workspace_id=str(workspace.id),
             agent_type=agent_type,
             updates=body.model_dump(exclude_none=True))
    
    raise HTTPException(
        status_code=501,
        detail="Agent configuration updates coming in Phase 15.1"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT EXECUTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/run", response_model=AgentRunResponse, status_code=202)
async def trigger_agent_run(
    body: AgentTriggerRequest,
    user: CurrentUser,
    workspace: Annotated[object, Depends(require_workspace_role("editor"))],
    ctx: WorkspaceCtx,
    db: DbSession,
    cache: Cache,
) -> AgentRunResponse:
    """Trigger manual agent execution.

    Requires at least the EDITOR workspace role (privileged + cost-incurring).

    Can run:
    - Full workflow (all 14 agents in orchestrated sequence)
    - Single agent (on-demand execution)
    """
    # Cost-DoS guard: cap how often the expensive multi-agent LLM workflow can
    # be manually triggered per workspace (the per-workspace budget hard-stop
    # in the LLM provider backs this up for sustained abuse).
    cooldown_key = f"agent_run_cooldown:{workspace.id}"
    if await cache.exists(cooldown_key):
        raise HTTPException(
            status_code=429,
            detail="Please wait a moment before triggering another agent run.",
        )
    await cache.set(cooldown_key, True, ttl_seconds=30)

    log.info("agent.trigger",
             workspace_id=str(workspace.id),
             user_id=str(user.id),
             agent_type=body.agent_type,
             trigger="manual")

    requested_agent = body.agent_type or "orchestrator"
    await publish_agent_event(
        workspace_id=workspace.id,
        event_type="agent_started",
        agent_type=requested_agent,
        data={
            "agent_type": requested_agent,
            "trigger": "manual",
            "requested_by": str(user.id),
        },
    )
    
    try:
        if body.agent_type:
            # Run single agent
            result_state = await run_single_agent(
                workspace_id=workspace.id,
                actor_id=str(user.id),
                agent_name=body.agent_type,
                db=db,
            )

            # run_single_agent doesn't persist an AgentRun row, so we materialise
            # one here from the returned state for the API response.
            stage_errors = result_state.get("errors") or None
            status_value = (
                AgentRunStatus.FAILED if stage_errors else AgentRunStatus.SUCCESS
            )
            agent_run = AgentRun(
                workspace_id=workspace.id,
                actor_id=str(user.id),
                trigger="manual",
                correlation_id=result_state["correlation_id"],
                run_type=body.agent_type,
                status=status_value,
                items_generated=len(result_state.get("content_ideas") or []),
                stage_errors=stage_errors,
                finished_at=datetime.now(timezone.utc),
            )
            db.add(agent_run)
            await db.commit()
            await db.refresh(agent_run)
            
        else:
            # Run full workflow
            result_state = await run_agent_workflow(
                workspace_id=workspace.id,
                actor_id=str(user.id),
                trigger="manual",
                db=db,
                budget_id=body.budget_id,
            )
            
            # Get the agent run record
            result = await db.execute(
                select(AgentRun)
                .where(
                    AgentRun.workspace_id == workspace.id,
                    AgentRun.correlation_id == result_state["correlation_id"],
                )
                .order_by(AgentRun.started_at.desc())
                .limit(1)
            )
            agent_run = result.scalar_one()
        
        # Calculate duration
        duration_ms = None
        if agent_run.finished_at:
            duration_ms = int((agent_run.finished_at - agent_run.started_at).total_seconds() * 1000)

        await publish_agent_event(
            workspace_id=workspace.id,
            event_type="agent_completed",
            agent_type=requested_agent,
            correlation_id=agent_run.correlation_id,
            data={
                "agent_type": requested_agent,
                "agent_run_id": str(agent_run.id),
                "status": agent_run.status.value,
                "correlation_id": agent_run.correlation_id,
                "items_generated": agent_run.items_generated,
                "tokens_used": agent_run.total_tokens_used,
                "cost_usd": agent_run.total_cost_usd,
                "duration_ms": duration_ms,
            },
        )
        
        return AgentRunResponse(
            id=agent_run.id,
            workspace_id=agent_run.workspace_id,
            run_type=agent_run.run_type,
            status=agent_run.status.value,
            trigger=agent_run.trigger,
            correlation_id=agent_run.correlation_id,
            items_fetched=agent_run.items_fetched,
            items_new=agent_run.items_new,
            items_scored=agent_run.items_scored,
            items_generated=agent_run.items_generated,
            gap_signals_found=agent_run.gap_signals_found,
            total_tokens_used=agent_run.total_tokens_used,
            total_cost_usd=agent_run.total_cost_usd,
            stage_errors=agent_run.stage_errors,
            started_at=agent_run.started_at,
            finished_at=agent_run.finished_at,
            duration_ms=duration_ms,
        )
        
    except Exception as e:
        log.error("agent.trigger.failed",
                  workspace_id=str(workspace.id),
                  error=str(e),
                  error_type=type(e).__name__)
        await publish_agent_event(
            workspace_id=workspace.id,
            event_type="agent_failed",
            agent_type=requested_agent,
            data={
                "agent_type": requested_agent,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> AgentStatusResponse:
    """Get overall agent system status for workspace.
    
    Returns:
        - Enabled agent count
        - Last run time
        - Success rate
        - Unread insights count
    """
    # Get today's runs
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(
            func.count(AgentRun.id).label("total"),
            func.sum(
                func.cast(AgentRun.status == AgentRunStatus.SUCCESS, db.bind.dialect.BIGINT)
            ).label("success"),
        )
        .where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.started_at >= today_start,
        )
    )
    stats = result.one()
    
    total_runs = stats.total or 0
    success_runs = stats.success or 0
    success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0.0
    
    # Get last run
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .order_by(AgentRun.started_at.desc())
        .limit(1)
    )
    last_run = result.scalar_one_or_none()
    
    # Get unread insights count
    result = await db.execute(
        select(func.count(WorkspaceInsight.id))
        .where(
            WorkspaceInsight.workspace_id == workspace.id,
            WorkspaceInsight.is_read == False,
            WorkspaceInsight.is_dismissed == False,
        )
    )
    unread_count = result.scalar_one()
    
    # Get today's insights count
    result = await db.execute(
        select(func.count(WorkspaceInsight.id))
        .where(
            WorkspaceInsight.workspace_id == workspace.id,
            WorkspaceInsight.created_at >= today_start,
        )
    )
    today_insights = result.scalar_one()
    
    return AgentStatusResponse(
        enabled_agents=14,  # TODO: Count from agent_configs
        last_run_at=last_run.started_at if last_run else None,
        next_scheduled_run=None,  # TODO: Calculate from schedule
        total_runs_today=total_runs,
        success_rate_today=round(success_rate, 1),
        total_insights_unread=unread_count,
        total_insights_today=today_insights,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/insights", response_model=PaginatedInsights)
async def list_insights(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    insight_type: InsightType | None = Query(None),
    agent_type: str | None = Query(None),
) -> PaginatedInsights:
    """Get paginated agent insights for workspace.
    
    Filters:
    - unread_only: Show only unread insights
    - insight_type: Filter by insight type
    - agent_type: Filter by agent that generated it
    
    Returns:
        Paginated list of insights ordered by priority DESC, created_at DESC
    """
    # Build query
    query = select(WorkspaceInsight).where(
        WorkspaceInsight.workspace_id == workspace.id,
        WorkspaceInsight.is_dismissed == False,
    )
    
    if unread_only:
        query = query.where(WorkspaceInsight.is_read == False)
    
    if insight_type:
        query = query.where(WorkspaceInsight.insight_type == insight_type)
    
    if agent_type:
        query = query.where(WorkspaceInsight.agent_type == agent_type)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Get paginated results
    query = query.order_by(
        WorkspaceInsight.priority.desc(),
        WorkspaceInsight.created_at.desc(),
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    insights = result.scalars().all()
    
    return PaginatedInsights(
        items=[AgentInsightResponse.model_validate(i) for i in insights],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.patch("/insights/{insight_id}", response_model=AgentInsightResponse)
async def update_insight(
    insight_id: uuid.UUID,
    body: AgentInsightUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> AgentInsightResponse:
    """Update insight status (mark as read, dismissed, actioned).
    
    Args:
        insight_id: Insight UUID
        body: Status updates
    
    Returns:
        Updated insight
    """
    # Get insight
    result = await db.execute(
        select(WorkspaceInsight).where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
    )
    insight = result.scalar_one_or_none()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Update fields
    if body.is_read is not None:
        insight.is_read = body.is_read
    if body.is_dismissed is not None:
        insight.is_dismissed = body.is_dismissed
    if body.is_actioned is not None:
        insight.is_actioned = body.is_actioned
    
    await db.commit()
    await db.refresh(insight)
    
    log.info("insight.updated",
             insight_id=str(insight_id),
             workspace_id=str(workspace.id),
             updates=body.model_dump(exclude_none=True))
    
    return AgentInsightResponse.model_validate(insight)


@router.delete("/insights/{insight_id}", status_code=204, response_model=None)
async def dismiss_insight(
    insight_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> None:
    """Dismiss an insight (soft delete).
    
    Args:
        insight_id: Insight UUID
    """
    result = await db.execute(
        update(WorkspaceInsight)
        .where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
        .values(is_dismissed=True)
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    await db.commit()
    
    log.info("insight.dismissed",
             insight_id=str(insight_id),
             workspace_id=str(workspace.id))


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET - REAL-TIME AGENT EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

async def _workspace_ids_for_user(user_id: str) -> list[uuid.UUID]:
    """Return active workspace IDs for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        return []

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkspaceMembership.workspace_id).where(
                WorkspaceMembership.user_id == user_uuid,
                WorkspaceMembership.invite_status == InviteStatus.ACTIVE,
            )
        )
        return [row[0] for row in result.all()]


async def _user_can_access_workspace(user_id: str, workspace_id: uuid.UUID) -> bool:
    """Verify a websocket subscription target belongs to the user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        return False

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_uuid,
                WorkspaceMembership.invite_status == InviteStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none() is not None


def _extract_workspace_id(message: dict) -> uuid.UUID | None:
    data = message.get("data")
    raw_workspace_id = message.get("workspace_id")
    if raw_workspace_id is None and isinstance(data, dict):
        raw_workspace_id = data.get("workspace_id")
    if not raw_workspace_id:
        return None
    try:
        return uuid.UUID(str(raw_workspace_id))
    except ValueError:
        return None


@router.websocket("/ws")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """Real-time agent event stream via WebSocket.
    
    Streams:
    - Agent run started/completed
    - New insights generated
    - Agent errors
    
    Protocol:
    - Client sends: {"type": "subscribe", "workspace_id": "uuid"}
    - Server sends: {"type": "agent_insight", "data": {...}}
    
    Authentication via token query parameter. In local development with
    DEV_BYPASS_AUTH=true, token may be omitted.
    """
    await websocket.accept()

    settings = get_settings()
    user_id = "dev"

    if token:
        try:
            payload = decode_token(token, expected_type="access")
            user_id = str(payload.get("sub") or "unknown")
        except Exception:
            await websocket.close(code=1008, reason="invalid_token")
            return
    elif settings.is_production or not getattr(settings, "DEV_BYPASS_AUTH", False):
        await websocket.close(code=1008, reason="authentication_required")
        return
    else:
        from app.core.dev_bypass import _DEV_USER_ID
        user_id = str(_DEV_USER_ID)

    send_lock = asyncio.Lock()
    subscriber = AgentEventSubscriber()

    async def send_json(payload: dict) -> None:
        async with send_lock:
            await websocket.send_json(payload)

    async def send_system_event(event_type: str, data: dict | None = None) -> None:
        await send_json({
            "type": event_type,
            "agent_type": "system",
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def subscribe_workspace(workspace_id: uuid.UUID) -> bool:
        if not await _user_can_access_workspace(user_id, workspace_id):
            await send_system_event(
                "agent_failed",
                {
                    "error": "workspace_access_denied",
                    "workspace_id": str(workspace_id),
                },
            )
            return False

        try:
            await subscriber.subscribe_workspace(workspace_id)
        except Exception as exc:
            log.warning(
                "agent_websocket.subscribe_failed",
                user_id=user_id,
                workspace_id=str(workspace_id),
                error=str(exc),
            )
            await send_system_event(
                "agent_failed",
                {
                    "error": "realtime_unavailable",
                    "workspace_id": str(workspace_id),
                },
            )
            return False

        await send_system_event(
            "connected",
            {
                "subscription": "added",
                "workspace_id": str(workspace_id),
            },
        )
        return True

    try:
        workspace_ids = await _workspace_ids_for_user(user_id)
        subscribed_workspace_ids: list[str] = []

        for workspace_id in workspace_ids:
            if await subscribe_workspace(workspace_id):
                subscribed_workspace_ids.append(str(workspace_id))

        log.info(
            "agent_websocket.connected",
            user_id=user_id,
            workspace_count=len(subscribed_workspace_ids),
        )
        await send_system_event(
            "connected",
            {
                "user_id": user_id,
                "workspace_ids": subscribed_workspace_ids,
            },
        )

        async def client_reader() -> None:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    await send_system_event("agent_failed", {"error": "invalid_json"})
                    continue

                message_type = message.get("type")
                if message_type == "ping":
                    await send_system_event("heartbeat", {"pong": True})
                    continue

                if message_type == "subscribe":
                    workspace_id = _extract_workspace_id(message)
                    if workspace_id is None:
                        await send_system_event("agent_failed", {"error": "invalid_workspace_id"})
                        continue
                    await subscribe_workspace(workspace_id)
                    continue

                if message_type == "unsubscribe":
                    workspace_id = _extract_workspace_id(message)
                    if workspace_id is None:
                        await send_system_event("agent_failed", {"error": "invalid_workspace_id"})
                        continue
                    await subscriber.unsubscribe_workspace(workspace_id)
                    await send_system_event(
                        "connected",
                        {
                            "subscription": "removed",
                            "workspace_id": str(workspace_id),
                        },
                    )

        async def event_writer() -> None:
            last_heartbeat = time.monotonic()
            last_redis_error = 0.0

            while True:
                try:
                    event = await subscriber.get_event(timeout=1.0)
                except Exception as exc:
                    now = time.monotonic()
                    log.warning("agent_websocket.redis_read_failed", error=str(exc))
                    if now - last_redis_error > 30:
                        last_redis_error = now
                        await send_system_event("agent_failed", {"error": "realtime_unavailable"})
                    await asyncio.sleep(5)
                    continue

                if event:
                    await send_json(event)

                now = time.monotonic()
                if now - last_heartbeat >= 30:
                    last_heartbeat = now
                    await send_system_event("heartbeat", {})

        tasks = {
            asyncio.create_task(client_reader()),
            asyncio.create_task(event_writer()),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            task.result()

    except WebSocketDisconnect:
        log.info("agent_websocket.disconnected", user_id=user_id)
    except Exception as e:
        log.error("agent_websocket.error", error=str(e))
        await websocket.close(code=1011, reason=str(e))
    finally:
        await subscriber.close()
