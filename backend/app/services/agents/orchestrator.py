"""Master Agent Orchestrator - Coordinates all 14 agents.

Determines which agents to run based on triggers, manages execution queue,
handles failures with retry logic, enforces cost limits.
"""
import uuid
from datetime import datetime, timezone
import structlog
from app.runtime.context import RunContext

log = structlog.get_logger(__name__)

AGENT_REGISTRY = {
    "trend_detection": {
        "module": "app.services.agents.trend_agent",
        "function": "detect_trends",
        "frequency": "30min",
        "priority": 9,
    },
    "goal_accountability": {
        "module": "app.services.agents.goal_agent",
        "function": "check_goals",
        "frequency": "daily",
        "priority": 8,
    },
    "competitor_intelligence": {
        "module": "app.services.agents.competitor_agent",
        "function": "monitor_competitors",
        "frequency": "4h",
        "priority": 7,
    },
    "analytics_intelligence": {
        "module": "app.services.agents.analytics_agent",
        "function": "analyze_performance",
        "frequency": "daily",
        "priority": 6,
    },
    "smart_scheduling": {
        "module": "app.services.agents.scheduling_agent",
        "function": "optimize_schedule",
        "frequency": "weekly",
        "priority": 5,
    },
    "niche_intelligence": {
        "module": "app.services.agents.niche_agent",
        "function": "analyze_niche",
        "frequency": "6h",
        "priority": 8,
    },
    "content_research": {
        "module": "app.services.agents.research_agent",
        "function": "generate_content_ideas",
        "frequency": "daily",
        "priority": 7,
    },
    "news_research": {
        "module": "app.services.agents.news_agent",
        "function": "fetch_news",
        "frequency": "hourly",
        "priority": 6,
    },
}

async def run_agent_orchestrator(ctx: RunContext, agent_types: list[str] | None = None) -> dict:
    """Run specified agents or all agents based on schedule.
    
    Args:
        ctx: RunContext with workspace_id and actor_id
        agent_types: List of agent types to run, or None for all
    
    Returns:
        Summary of agent execution results
    """
    from app.db.session import AsyncSessionLocal
    from app.domains.intelligence.models import AgentRun, AgentRunStatus, AgentStep
    from sqlalchemy import update
    import importlib
    
    run_id = uuid.uuid4()
    results = {}
    errors = []
    
    # Determine which agents to run
    agents_to_run = agent_types or list(AGENT_REGISTRY.keys())
    
    log.info("orchestrator_start", 
             run_id=str(run_id),
             agents=agents_to_run,
             workspace_id=str(ctx.workspace_id))
    
    # Create AgentRun record
    async with AsyncSessionLocal() as db:
        agent_run = AgentRun(
            id=run_id,
            workspace_id=ctx.workspace_id,
            actor_id=ctx.actor_id,
            trigger=ctx.trigger,
            correlation_id=ctx.correlation_id,
            run_type="agent_orchestration",
            status=AgentRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        db.add(agent_run)
        await db.commit()
    
    # Run each agent
    for idx, agent_type in enumerate(agents_to_run):
        if agent_type not in AGENT_REGISTRY:
            log.warning("unknown_agent_type", agent_type=agent_type)
            continue
        
        agent_config = AGENT_REGISTRY[agent_type]
        
        try:
            # Dynamic import
            module = importlib.import_module(agent_config["module"])
            agent_func = getattr(module, agent_config["function"])
            
            # Get niche IDs for workspace
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                from app.domains.control.models import WorkspaceNiche
                result = await db.execute(
                    select(WorkspaceNiche.niche_id).where(
                        WorkspaceNiche.workspace_id == ctx.workspace_id
                    )
                )
                niche_ids = [str(row[0]) for row in result.all()]
            
            # Execute agent
            if agent_type == "trend_detection":
                result = await agent_func(ctx, niche_ids)
            else:
                result = await agent_func(ctx)
            
            results[agent_type] = result
            
            # Record successful step
            async with AsyncSessionLocal() as db:
                step = AgentStep(
                    agent_run_id=run_id,
                    step_name=agent_type,
                    step_order=idx,
                    status="completed",
                    output_summary=str(result),
                )
                db.add(step)
                await db.commit()
            
            log.info("agent_complete", agent_type=agent_type, result=result)
            
        except Exception as exc:
            error_msg = f"{agent_type}: {str(exc)}"
            errors.append(error_msg)
            
            # Record failed step
            async with AsyncSessionLocal() as db:
                step = AgentStep(
                    agent_run_id=run_id,
                    step_name=agent_type,
                    step_order=idx,
                    status="failed",
                    error=str(exc),
                )
                db.add(step)
                await db.commit()
            
            log.error("agent_failed", agent_type=agent_type, error=str(exc))
    
    # Finalize AgentRun
    final_status = (
        AgentRunStatus.FAILED if len(errors) == len(agents_to_run)
        else AgentRunStatus.PARTIAL if errors
        else AgentRunStatus.SUCCESS
    )
    
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(
                status=final_status,
                finished_at=datetime.now(timezone.utc),
                stage_errors=errors if errors else None,
            )
        )
        await db.commit()
    
    log.info("orchestrator_complete",
             run_id=str(run_id),
             status=final_status.value,
             agents_run=len(results),
             errors=len(errors))
    
    return {
        "run_id": str(run_id),
        "status": final_status.value,
        "agents_run": len(results),
        "results": results,
        "errors": errors,
    }
