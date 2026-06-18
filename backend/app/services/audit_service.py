"""Audit Service - Append-only audit trail for all sensitive actions.

Phase 12: Audit & Governance
Every high-impact action needs a clear source, actor, context, and decision trail.
"""
import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domains.control.models import AuditLog
from app.runtime.correlation import get_correlation_id

log = structlog.get_logger(__name__)


class AuditService:
    """Service for creating and querying audit logs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(
        self,
        action_type: str,
        resource_type: str,
        actor_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None,
        reason: Optional[str] = None,
        before_summary: Optional[dict[str, Any]] = None,
        after_summary: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an audit log entry.
        
        Args:
            action_type: Type of action (e.g., "workspace.created", "post.published")
            resource_type: Type of resource (e.g., "workspace", "post", "agent_run")
            actor_id: User ID or "system"
            workspace_id: Workspace context (if applicable)
            resource_id: ID of the affected resource
            reason: Human-readable reason for the action
            before_summary: State before the action
            after_summary: State after the action
        
        Returns:
            Created AuditLog instance
        """
        correlation_id = get_correlation_id()
        
        audit_log = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            reason=reason,
            before_summary=before_summary,
            after_summary=after_summary,
            created_at=datetime.now(timezone.utc),
        )
        
        self.db.add(audit_log)
        await self.db.flush()
        
        log.info(
            "audit_log_created",
            audit_id=str(audit_log.id),
            action_type=action_type,
            resource_type=resource_type,
            actor_id=actor_id,
            workspace_id=str(workspace_id) if workspace_id else None,
            correlation_id=correlation_id,
        )
        
        return audit_log
    
    async def get_workspace_audit_trail(
        self,
        workspace_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> list[AuditLog]:
        """Get audit trail for a workspace.
        
        Args:
            workspace_id: Workspace to query
            limit: Maximum number of records
            offset: Pagination offset
            action_type: Filter by action type
            resource_type: Filter by resource type
        
        Returns:
            List of audit log entries
        """
        query = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
        
        if action_type:
            query = query.where(AuditLog.action_type == action_type)
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[AuditLog]:
        """Get all audit logs for a correlation ID (entire request trace).
        
        Args:
            correlation_id: Correlation ID to trace
        
        Returns:
            List of audit log entries in chronological order
        """
        query = (
            select(AuditLog)
            .where(AuditLog.correlation_id == correlation_id)
            .order_by(AuditLog.created_at.asc())
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())


# Convenience functions for common audit actions

async def audit_workspace_created(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    actor_id: str,
    workspace_data: dict[str, Any],
) -> None:
    """Audit workspace creation."""
    service = AuditService(db)
    await service.log_action(
        action_type="workspace.created",
        resource_type="workspace",
        actor_id=actor_id,
        workspace_id=workspace_id,
        resource_id=str(workspace_id),
        after_summary=workspace_data,
    )


async def audit_subscription_changed(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    actor_id: str,
    old_tier: str,
    new_tier: str,
    reason: str,
) -> None:
    """Audit subscription tier change."""
    service = AuditService(db)
    await service.log_action(
        action_type="subscription.changed",
        resource_type="workspace",
        actor_id=actor_id,
        workspace_id=workspace_id,
        resource_id=str(workspace_id),
        reason=reason,
        before_summary={"tier": old_tier},
        after_summary={"tier": new_tier},
    )


async def audit_agent_run_started(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    agent_run_id: uuid.UUID,
    actor_id: str,
    agent_type: str,
    trigger: str,
) -> None:
    """Audit agent run start."""
    service = AuditService(db)
    await service.log_action(
        action_type="agent_run.started",
        resource_type="agent_run",
        actor_id=actor_id,
        workspace_id=workspace_id,
        resource_id=str(agent_run_id),
        after_summary={"agent_type": agent_type, "trigger": trigger},
    )


async def audit_publish_attempt(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    publish_job_id: uuid.UUID,
    actor_id: str,
    platform: str,
    status: str,
) -> None:
    """Audit publish attempt."""
    service = AuditService(db)
    await service.log_action(
        action_type="publish.attempted",
        resource_type="publish_job",
        actor_id=actor_id,
        workspace_id=workspace_id,
        resource_id=str(publish_job_id),
        after_summary={"platform": platform, "status": status},
    )


async def audit_approval_decision(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    approval_id: uuid.UUID,
    actor_id: str,
    decision: str,
    reason: Optional[str] = None,
) -> None:
    """Audit approval decision."""
    service = AuditService(db)
    await service.log_action(
        action_type="approval.decided",
        resource_type="approval_request",
        actor_id=actor_id,
        workspace_id=workspace_id,
        resource_id=str(approval_id),
        reason=reason,
        after_summary={"decision": decision},
    )
