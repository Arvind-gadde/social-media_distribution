"""RunContext — mandatory execution context for all tenant-owned work.

Every async job, agent run, and API handler that touches workspace-owned
data MUST carry a RunContext. This is the single most important governance
primitive in the system.

Rules:
  - Required for all tenant-owned async work.
  - Must be logged at every domain boundary.
  - No worker may infer workspace context from "current user" or "first active user".
  - correlation_id propagates from API/webhook ingress through workers and provider calls.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RunContext:
    """Immutable execution context that flows through the entire system.

    Attributes:
        workspace_id: The tenant boundary. All data access scoped to this.
        actor_id: Who triggered this — a user UUID or "system".
        trigger: How this execution was initiated.
        correlation_id: UUID for distributed tracing. Propagated everywhere.
        budget_id: Optional budget policy to enforce cost limits.
        approval_policy: Controls whether high-risk actions need human approval.
    """
    workspace_id: uuid.UUID
    actor_id: str  # UUID string or "system"
    trigger: Literal["manual", "schedule", "webhook", "retry", "operator", "system"]
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    budget_id: str | None = None
    approval_policy: Literal["auto", "manual", "tiered"] = "auto"

    def to_log_dict(self) -> dict:
        """Structured logging fields — attach to every log entry."""
        return {
            "workspace_id": str(self.workspace_id),
            "actor_id": self.actor_id,
            "trigger": self.trigger,
            "correlation_id": self.correlation_id,
        }

    def to_celery_dict(self) -> dict:
        """Serialize for Celery task kwargs."""
        return {
            "workspace_id": str(self.workspace_id),
            "actor_id": self.actor_id,
            "trigger": self.trigger,
            "correlation_id": self.correlation_id,
            "budget_id": self.budget_id,
            "approval_policy": self.approval_policy,
        }

    @classmethod
    def from_celery_dict(cls, data: dict) -> "RunContext":
        """Deserialize from Celery task kwargs."""
        return cls(
            workspace_id=uuid.UUID(data["workspace_id"]),
            actor_id=data["actor_id"],
            trigger=data["trigger"],
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            budget_id=data.get("budget_id"),
            approval_policy=data.get("approval_policy", "auto"),
        )

    @classmethod
    def system_context(cls, workspace_id: uuid.UUID) -> "RunContext":
        """Create a system-triggered context for automated operations."""
        return cls(
            workspace_id=workspace_id,
            actor_id="system",
            trigger="system",
        )

    @classmethod
    def schedule_context(cls, workspace_id: uuid.UUID) -> "RunContext":
        """Create a schedule-triggered context for cron jobs."""
        return cls(
            workspace_id=workspace_id,
            actor_id="system",
            trigger="schedule",
        )
