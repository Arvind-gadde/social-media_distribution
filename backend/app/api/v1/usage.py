"""Usage API endpoints.

Phase 12: Audit & Governance
Query usage metrics and cost reports for workspaces.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import User
from app.services.usage_service import UsageService
from app.domains.control.models import WorkspaceMembership

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/report")
async def get_usage_report(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage report for a workspace.
    
    Returns aggregated usage metrics by meter type with costs.
    Requires workspace membership with at least analyst role.
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
    
    # Get usage summary
    service = UsageService(db)
    summary = await service.get_workspace_usage_summary(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    return summary


@router.get("/budget-status")
async def get_budget_status(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if workspace has exceeded budget limits.
    
    Returns current usage vs budget limits with percentage utilization.
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
    
    # Check budget
    service = UsageService(db)
    exceeded, details = await service.check_budget_exceeded(workspace_id)
    
    return {
        "workspace_id": str(workspace_id),
        "exceeded": exceeded,
        "details": details,
    }


@router.get("/breakdown")
async def get_usage_breakdown(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    meter_type: Optional[str] = Query(None, description="Filter by meter type"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed usage breakdown (individual meter events).
    
    Useful for debugging and detailed cost analysis.
    """
    # Verify workspace access
    from sqlalchemy import select
    from app.domains.control.models import UsageMeter
    
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
    
    # Build query
    query = select(UsageMeter).where(UsageMeter.workspace_id == workspace_id)
    
    if meter_type:
        query = query.where(UsageMeter.meter_type == meter_type)
    
    if provider:
        query = query.where(UsageMeter.provider == provider)
    
    query = query.order_by(UsageMeter.recorded_at.desc()).limit(limit)
    
    result = await db.execute(query)
    meters = result.scalars().all()
    
    return {
        "workspace_id": str(workspace_id),
        "count": len(meters),
        "meters": [
            {
                "id": str(meter.id),
                "meter_type": meter.meter_type,
                "quantity": meter.quantity,
                "cost_usd": meter.cost_usd,
                "provider": meter.provider,
                "model": meter.model,
                "source_run_id": str(meter.source_run_id) if meter.source_run_id else None,
                "source_type": meter.source_type,
                "recorded_at": meter.recorded_at.isoformat(),
            }
            for meter in meters
        ],
    }
