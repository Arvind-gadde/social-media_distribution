"""Approvals API — list pending, approve/reject, expire stale.

Workspace-scoped approval workflow management.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.execution.models import ApprovalRequest, ApprovalDecision
from app.services.approval_service import ApprovalService
from app.exceptions import NotFoundError

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _approval_to_dict(req: ApprovalRequest) -> dict:
    return {
        "id": str(req.id),
        "workspace_id": str(req.workspace_id),
        "resource_type": req.resource_type,
        "resource_id": req.resource_id,
        "policy_key": req.policy_key,
        "requested_by": req.requested_by,
        "decided_by": req.decided_by,
        "decision": req.decision.value,
        "reason": req.reason,
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "expires_at": req.expires_at.isoformat() if req.expires_at else None,
        "created_at": req.created_at.isoformat(),
    }


@router.get("")
async def list_approvals(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    status: str | None = Query(None, description="Filter by decision: pending, approved, rejected, expired"),
    resource_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """List approval requests for the workspace."""
    filters = [ApprovalRequest.workspace_id == workspace.id]
    if status:
        try:
            filters.append(ApprovalRequest.decision == ApprovalDecision(status))
        except ValueError:
            pass
    if resource_type:
        filters.append(ApprovalRequest.resource_type == resource_type)

    result = await db.execute(
        select(ApprovalRequest)
        .where(and_(*filters))
        .order_by(ApprovalRequest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    approvals = result.scalars().all()

    count_result = await db.execute(
        select(func.count(ApprovalRequest.id)).where(and_(*filters))
    )
    total = count_result.scalar() or 0

    # Count pending
    pending_result = await db.execute(
        select(func.count(ApprovalRequest.id)).where(
            and_(
                ApprovalRequest.workspace_id == workspace.id,
                ApprovalRequest.decision == ApprovalDecision.PENDING,
            )
        )
    )
    pending_count = pending_result.scalar() or 0

    return JSONResponse({
        "approvals": [_approval_to_dict(a) for a in approvals],
        "total": total,
        "pending_count": pending_count,
    })


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Get a specific approval request."""
    result = await db.execute(
        select(ApprovalRequest).where(
            and_(
                ApprovalRequest.id == uuid.UUID(approval_id),
                ApprovalRequest.workspace_id == workspace.id,
            )
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise NotFoundError("ApprovalRequest", approval_id)

    return JSONResponse({"approval": _approval_to_dict(approval)})


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    body: dict,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Approve a pending request."""
    svc = ApprovalService(db)
    try:
        request = await svc.decide(
            approval_id=uuid.UUID(approval_id),
            decision=ApprovalDecision.APPROVED,
            decided_by=str(current_user.id),
            reason=body.get("reason"),
        )
        await db.commit()
        return JSONResponse({"approval": _approval_to_dict(request)})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    body: dict,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Reject a pending request."""
    svc = ApprovalService(db)
    try:
        request = await svc.decide(
            approval_id=uuid.UUID(approval_id),
            decision=ApprovalDecision.REJECTED,
            decided_by=str(current_user.id),
            reason=body.get("reason"),
        )
        await db.commit()
        return JSONResponse({"approval": _approval_to_dict(request)})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
