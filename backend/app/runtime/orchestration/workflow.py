"""LangGraph Workflow - Agent orchestration workflow.

Phase 13: Agent Orchestration

Creates and executes the complete agent workflow graph with all 14 agents.
"""
import uuid
import structlog
from datetime import datetime, timezone
from typing import Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .state import AgentState
from .nodes import (
    niche_intelligence_agent,
    trend_detection_agent,
    analytics_intelligence_agent,
    competitor_intelligence_agent,
    content_ideation_agent,
    goal_accountability_agent,
    news_research_agent,
    tips_tricks_agent,
    smart_scheduling_agent,
    growth_optimization_agent,
    video_intelligence_agent,
    predictive_virality_agent,
    collaboration_business_agent,
    approval_gate,
)
from app.services.audit_service import AuditService
from app.domains.intelligence.models import AgentRun, AgentStep
from app.runtime.correlation import get_correlation_id

log = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW CREATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_agent_workflow() -> StateGraph:
    """Create the agent orchestration workflow graph.
    
    Workflow structure:
    1. Parallel data gathering: Niche, Trend, Competitor, News agents
    2. Analysis: Analytics agent synthesizes data
    3. Generation: Content ideation, Goal tracking, Tips, Scheduling
    4. Optimization: Growth, Video, Virality prediction
    5. Business: Collaboration agent
    6. Gate: Approval gate checks policies
    
    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(AgentState)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 1: DATA GATHERING (Parallel execution)
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("niche_intelligence", niche_intelligence_agent)
    workflow.add_node("trend_detection", trend_detection_agent)
    workflow.add_node("competitor_intelligence", competitor_intelligence_agent)
    workflow.add_node("news_research", news_research_agent)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 2: ANALYSIS & SYNTHESIS
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("analytics_intelligence", analytics_intelligence_agent)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 3: GENERATION & PLANNING (Parallel execution)
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("content_ideation", content_ideation_agent)
    workflow.add_node("goal_accountability", goal_accountability_agent)
    workflow.add_node("tips_tricks", tips_tricks_agent)
    workflow.add_node("smart_scheduling", smart_scheduling_agent)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 4: OPTIMIZATION (Parallel execution)
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("growth_optimization", growth_optimization_agent)
    workflow.add_node("video_intelligence", video_intelligence_agent)
    workflow.add_node("predictive_virality", predictive_virality_agent)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 5: BUSINESS AUTOMATION
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("collaboration_business", collaboration_business_agent)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PHASE 6: APPROVAL GATE
    # ───────────────────────────────────────────────────────────────────────────
    workflow.add_node("approval_gate", approval_gate)
    
    # ───────────────────────────────────────────────────────────────────────────
    # WORKFLOW EDGES
    # ───────────────────────────────────────────────────────────────────────────
    
    # Entry point: Start with data gathering agents in parallel
    workflow.set_entry_point("niche_intelligence")
    
    # Phase 1: Data gathering (parallel) → Analytics
    workflow.add_edge("niche_intelligence", "analytics_intelligence")
    workflow.add_edge("trend_detection", "analytics_intelligence")
    workflow.add_edge("competitor_intelligence", "analytics_intelligence")
    workflow.add_edge("news_research", "analytics_intelligence")
    
    # Phase 2: Analytics → Generation agents (parallel)
    workflow.add_edge("analytics_intelligence", "content_ideation")
    workflow.add_edge("analytics_intelligence", "goal_accountability")
    workflow.add_edge("analytics_intelligence", "tips_tricks")
    workflow.add_edge("analytics_intelligence", "smart_scheduling")
    
    # Phase 3: Generation → Optimization agents (parallel)
    workflow.add_edge("content_ideation", "growth_optimization")
    workflow.add_edge("goal_accountability", "growth_optimization")
    workflow.add_edge("tips_tricks", "video_intelligence")
    workflow.add_edge("smart_scheduling", "predictive_virality")
    
    # Phase 4: Optimization → Business
    workflow.add_edge("growth_optimization", "collaboration_business")
    workflow.add_edge("video_intelligence", "collaboration_business")
    workflow.add_edge("predictive_virality", "collaboration_business")
    
    # Phase 5: Business → Approval gate
    workflow.add_edge("collaboration_business", "approval_gate")
    
    # Phase 6: Approval gate → End
    workflow.add_edge("approval_gate", END)
    
    return workflow.compile()


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

async def run_agent_workflow(
    workspace_id: uuid.UUID,
    actor_id: str,
    trigger: Literal["manual", "schedule", "webhook", "retry", "operator"],
    db: AsyncSession,
    budget_id: uuid.UUID | None = None,
) -> dict:
    """Execute the agent workflow for a workspace.
    
    Args:
        workspace_id: Workspace to run agents for
        actor_id: User ID or "system"
        trigger: What triggered this run
        db: Database session
        budget_id: Optional budget policy to enforce
    
    Returns:
        Final state dict with results
    
    Raises:
        Exception: If workflow execution fails
    """
    correlation_id = get_correlation_id()
    
    # Create agent run record
    agent_run = AgentRun(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        actor_id=actor_id,
        trigger=trigger,
        correlation_id=correlation_id,
        budget_id=budget_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(agent_run)
    await db.flush()
    
    log.info("agent_workflow.started",
             agent_run_id=str(agent_run.id),
             workspace_id=str(workspace_id),
             correlation_id=correlation_id,
             trigger=trigger)
    
    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action="agent_workflow.started",
        resource_type="agent_run",
        resource_id=agent_run.id,
        details={
            "trigger": trigger,
            "budget_id": str(budget_id) if budget_id else None,
        },
    )
    
    # Initialize state
    initial_state: AgentState = {
        "workspace_id": str(workspace_id),
        "actor_id": actor_id,
        "trigger": trigger,
        "correlation_id": correlation_id,
        "budget_id": str(budget_id) if budget_id else None,
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "content_ideas": [],
        "approvals_needed": [],
        "approval_decisions": {},
        "errors": [],
        "retry_count": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Create workflow
    workflow = create_agent_workflow()
    
    try:
        # Execute workflow
        log.info("agent_workflow.executing",
                 agent_run_id=str(agent_run.id),
                 workspace_id=str(workspace_id))
        
        final_state = await workflow.ainvoke(initial_state, {"db": db})
        
        # Calculate duration
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - agent_run.started_at).total_seconds() * 1000)
        
        # Update agent run
        agent_run.status = "completed"
        agent_run.completed_at = completed_at
        agent_run.duration_ms = duration_ms
        agent_run.output_data = {
            "insights_count": len(final_state["insights"]),
            "ideas_count": len(final_state["content_ideas"]),
            "agents_executed": final_state["active_agents"],
            "approval_decisions": final_state["approval_decisions"],
        }
        
        # Mark as completed
        final_state["completed_at"] = completed_at.isoformat()
        
        await db.commit()
        
        # Audit log
        await audit_service.log(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="agent_workflow.completed",
            resource_type="agent_run",
            resource_id=agent_run.id,
            details={
                "duration_ms": duration_ms,
                "insights_count": len(final_state["insights"]),
                "ideas_count": len(final_state["content_ideas"]),
                "agents_executed": final_state["active_agents"],
            },
        )
        
        log.info("agent_workflow.completed",
                 agent_run_id=str(agent_run.id),
                 workspace_id=str(workspace_id),
                 duration_ms=duration_ms,
                 insights_count=len(final_state["insights"]),
                 ideas_count=len(final_state["content_ideas"]),
                 agents_executed=len(final_state["active_agents"]))
        
        return final_state
        
    except Exception as e:
        log.error("agent_workflow.failed",
                  agent_run_id=str(agent_run.id),
                  workspace_id=str(workspace_id),
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Update agent run
        agent_run.status = "failed"
        agent_run.completed_at = datetime.now(timezone.utc)
        agent_run.error_message = str(e)
        
        await db.commit()
        
        # Audit log
        await audit_service.log(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="agent_workflow.failed",
            resource_type="agent_run",
            resource_id=agent_run.id,
            details={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTIVE AGENT EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

async def run_single_agent(
    workspace_id: uuid.UUID,
    actor_id: str,
    agent_name: str,
    db: AsyncSession,
) -> dict:
    """Run a single agent instead of the full workflow.
    
    Useful for:
    - On-demand agent execution
    - Testing individual agents
    - Triggered agent runs (e.g., video upload → video intelligence agent)
    
    Args:
        workspace_id: Workspace to run agent for
        actor_id: User ID or "system"
        agent_name: Name of agent to run
        db: Database session
    
    Returns:
        Agent result dict
    
    Raises:
        ValueError: If agent_name is invalid
    """
    # Map agent names to functions
    agent_map = {
        "niche_intelligence": niche_intelligence_agent,
        "trend_detection": trend_detection_agent,
        "analytics_intelligence": analytics_intelligence_agent,
        "competitor_intelligence": competitor_intelligence_agent,
        "content_ideation": content_ideation_agent,
        "goal_accountability": goal_accountability_agent,
        "news_research": news_research_agent,
        "tips_tricks": tips_tricks_agent,
        "smart_scheduling": smart_scheduling_agent,
        "growth_optimization": growth_optimization_agent,
        "video_intelligence": video_intelligence_agent,
        "predictive_virality": predictive_virality_agent,
        "collaboration_business": collaboration_business_agent,
    }
    
    if agent_name not in agent_map:
        raise ValueError(f"Invalid agent name: {agent_name}")
    
    correlation_id = get_correlation_id()
    
    log.info("single_agent.started",
             workspace_id=str(workspace_id),
             agent_name=agent_name,
             correlation_id=correlation_id)
    
    # Initialize minimal state
    state: AgentState = {
        "workspace_id": str(workspace_id),
        "actor_id": actor_id,
        "trigger": "manual",
        "correlation_id": correlation_id,
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "content_ideas": [],
        "approvals_needed": [],
        "approval_decisions": {},
        "errors": [],
        "retry_count": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Execute agent
    agent_func = agent_map[agent_name]
    result_state = await agent_func(state, db)
    
    log.info("single_agent.completed",
             workspace_id=str(workspace_id),
             agent_name=agent_name,
             insights_count=len(result_state["insights"]))
    
    return result_state
