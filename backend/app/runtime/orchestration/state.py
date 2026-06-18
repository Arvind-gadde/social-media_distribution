"""LangGraph state schema for agent orchestration.

Phase 13: Agent Orchestration
"""
from typing import TypedDict, Annotated, Literal
from typing_extensions import NotRequired
import operator


class AgentState(TypedDict):
    """State shared across all agent nodes in the graph.
    
    This state is passed between agent nodes and accumulates results
    from each step of the workflow.
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT — Who, what, when, why
    # ═══════════════════════════════════════════════════════════════════════
    workspace_id: str
    actor_id: str  # User ID or "system"
    trigger: Literal["manual", "schedule", "webhook", "retry", "operator"]
    correlation_id: str
    budget_id: NotRequired[str]
    
    # ═══════════════════════════════════════════════════════════════════════
    # AGENT EXECUTION — Results from each agent
    # ═══════════════════════════════════════════════════════════════════════
    active_agents: list[str]  # Agents that have executed
    agent_results: Annotated[dict, operator.or_]  # Merge results from parallel agents
    insights: list[dict]  # Workspace insights generated
    content_ideas: list[dict]  # Content ideas generated
    
    # ═══════════════════════════════════════════════════════════════════════
    # APPROVAL WORKFLOW — Gated actions
    # ═══════════════════════════════════════════════════════════════════════
    approvals_needed: list[str]  # Actions requiring approval
    approval_decisions: dict[str, str]  # Approval decisions
    
    # ═══════════════════════════════════════════════════════════════════════
    # ERROR HANDLING — Failures and retries
    # ═══════════════════════════════════════════════════════════════════════
    errors: list[str]  # Error messages
    retry_count: int  # Number of retries
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA — Timestamps and tracking
    # ═══════════════════════════════════════════════════════════════════════
    started_at: str  # ISO timestamp
    completed_at: NotRequired[str]  # ISO timestamp
