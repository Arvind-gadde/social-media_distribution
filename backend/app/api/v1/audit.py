"""Audit API endpoints.

Phase 12: Audit & Governance
Query audit trail for compliance, debugging, and security investigations.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import User
from app.services.audit_service import AuditService
from app.domains.control.models import Workspace, WorkspaceMembership

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
async def get_audit_logs(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit trail for a workspace.
    
    Requires workspace membership with at least viewer role.
    """
    # Verify workspace access
    from sqlalchemy import select
    membership_query = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == current_user.id,
    )
    result = await db.execute(membership_query)
    membership = result.scalar_one_or_none()
    
    if not membership:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace",
        )
    
    # Get audit logs
    service = AuditService(db)
    logs = await service.get_workspace_audit_trail(
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
        action_type=action_type,
        resource_type=resource_type,
    )
    
    return {
        "workspace_id": str(workspace_id),
        "count": len(logs),
        "logs": [
            {
                "id": str(log.id),
                "action_type": log.action_type,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_id": log.actor_id,
                "correlation_id": log.correlation_id,
                "reason": log.reason,
                "before_summary": log.before_summary,
                "after_summary": log.after_summary,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/trace/{correlation_id}")
async def get_audit_trace(
    correlation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete audit trail for a correlation ID (entire request trace).
    
    Useful for debugging and understanding the full execution path of a request.
    """
    service = AuditService(db)
    logs = await service.get_by_correlation_id(correlation_id)
    
    # Filter logs to only workspaces user has access to
    from sqlalchemy import select
    user_workspace_ids_query = select(WorkspaceMembership.workspace_id).where(
        WorkspaceMembership.user_id == current_user.id,
    )
    result = await db.execute(user_workspace_ids_query)
    user_workspace_ids = {row[0] for row in result.all()}
    
    filtered_logs = [
        log for log in logs
        if log.workspace_id is None or log.workspace_id in user_workspace_ids
    ]
    
    return {
        "correlation_id": correlation_id,
        "count": len(filtered_logs),
        "trace": [
            {
                "id": str(log.id),
                "workspace_id": str(log.workspace_id) if log.workspace_id else None,
                "action_type": log.action_type,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_id": log.actor_id,
                "reason": log.reason,
                "before_summary": log.before_summary,
                "after_summary": log.after_summary,
                "created_at": log.created_at.isoformat(),
            }
            for log in filtered_logs
        ],
    }
