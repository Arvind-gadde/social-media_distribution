"""Approval Service - Gated actions requiring human approval.

Phase 12: Audit & Governance
High-risk actions such as auto-publishing, billing-sensitive operations,
or partner-facing outputs need explicit approval policies and audit trails.
"""
import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.domains.execution.models import ApprovalRequest
from app.domains.control.models import Workspace, BudgetPolicy

log = structlog.get_logger(__name__)


class ApprovalDecision:
    """Approval decision constants."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalService:
    """Service for managing approval workflows."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_approval_request(
        self,
        workspace_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        policy_key: str,
        requested_by: str,
        reason: Optional[str] = None,
        request_data: Optional[dict] = None,
        expires_in_hours: int = 24,
    ) -> ApprovalRequest:
        """Create an approval request.
        
        Args:
            workspace_id: Workspace context
            resource_type: Type of resource (e.g., "publish_job", "agent_run")
            resource_id: ID of the resource
            policy_key: Policy that triggered approval (e.g., "high_cost_operation")
            requested_by: User ID or "system"
            reason: Human-readable reason
            request_data: Additional context data
            expires_in_hours: Hours until request expires
        
        Returns:
            Created ApprovalRequest instance
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        approval_request = ApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            policy_key=policy_key,
            requested_by=requested_by,
            decision=ApprovalDecision.PENDING,
            reason=reason,
            request_data=request_data,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        self.db.add(approval_request)
        await self.db.flush()
        
        log.info(
            "approval_request_created",
            approval_id=str(approval_request.id),
            workspace_id=str(workspace_id),
            resource_type=resource_type,
            policy_key=policy_key,
            requested_by=requested_by,
        )
        
        return approval_request
    
    async def decide_approval(
        self,
        approval_id: uuid.UUID,
        decided_by: str,
        decision: str,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        """Make a decision on an approval request.
        
        Args:
            approval_id: Approval request ID
            decided_by: User ID making the decision
            decision: "approved" or "rejected"
            reason: Reason for the decision
        
        Returns:
            Updated ApprovalRequest instance
        
        Raises:
            HTTPException: If approval not found or already decided
        """
        query = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await self.db.execute(query)
        approval = result.scalar_one_or_none()
        
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request {approval_id} not found",
            )
        
        if approval.decision != ApprovalDecision.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval request already {approval.decision}",
            )
        
        # Check if expired
        if approval.expires_at and approval.expires_at < datetime.now(timezone.utc):
            approval.decision = ApprovalDecision.EXPIRED
            approval.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Approval request has expired",
            )
        
        # Update decision
        approval.decided_by = decided_by
        approval.decision = decision
        approval.decided_at = datetime.now(timezone.utc)
        approval.updated_at = datetime.now(timezone.utc)
        
        if reason:
            approval.reason = f"{approval.reason or ''}\nDecision: {reason}".strip()
        
        await self.db.flush()
        
        log.info(
            "approval_decided",
            approval_id=str(approval_id),
            decision=decision,
            decided_by=decided_by,
            workspace_id=str(approval.workspace_id),
        )
        
        return approval
    
    async def get_pending_approvals(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        """Get pending approval requests for a workspace.
        
        Args:
            workspace_id: Workspace to query
            limit: Maximum number of records
        
        Returns:
            List of pending approval requests
        """
        query = (
            select(ApprovalRequest)
            .where(
                ApprovalRequest.workspace_id == workspace_id,
                ApprovalRequest.decision == ApprovalDecision.PENDING,
            )
            .order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def expire_old_approvals(self) -> int:
        """Expire approval requests that have passed their expiration time.
        
        Returns:
            Number of approvals expired
        """
        now = datetime.now(timezone.utc)
        
        query = select(ApprovalRequest).where(
            ApprovalRequest.decision == ApprovalDecision.PENDING,
            ApprovalRequest.expires_at < now,
        )
        
        result = await self.db.execute(query)
        expired_approvals = result.scalars().all()
        
        count = 0
        for approval in expired_approvals:
            approval.decision = ApprovalDecision.EXPIRED
            approval.updated_at = now
            count += 1
        
        await self.db.flush()
        
        if count > 0:
            log.info("approvals_expired", count=count)
        
        return count
    
    async def check_approval_required(
        self,
        workspace_id: uuid.UUID,
        operation_cost_usd: float,
    ) -> bool:
        """Check if an operation requires approval based on cost.
        
        Args:
            workspace_id: Workspace context
            operation_cost_usd: Estimated cost of operation
        
        Returns:
            True if approval required, False otherwise
        """
        query = select(BudgetPolicy).where(
            BudgetPolicy.workspace_id == workspace_id,
            BudgetPolicy.is_active == True,
        )
        result = await self.db.execute(query)
        budget_policy = result.scalar_one_or_none()
        
        if not budget_policy:
            return False
        
        return operation_cost_usd >= budget_policy.approval_required_above_usd


# Convenience functions for common approval workflows

async def require_approval_for_high_cost_operation(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    resource_type: str,
    resource_id: str,
    requested_by: str,
    estimated_cost_usd: float,
    operation_description: str,
) -> ApprovalRequest:
    """Create approval request for high-cost operation.
    
    Raises:
        HTTPException: If approval is required (HTTP 202 Accepted)
    """
    service = ApprovalService(db)
    
    approval = await service.create_approval_request(
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        policy_key="high_cost_operation",
        requested_by=requested_by,
        reason=f"Operation cost ${estimated_cost_usd:.2f} exceeds approval threshold",
        request_data={
            "estimated_cost_usd": estimated_cost_usd,
            "operation_description": operation_description,
        },
    )
    
    raise HTTPException(
        status_code=status.HTTP_202_ACCEPTED,
        detail={
            "message": "Approval required for high-cost operation",
            "approval_id": str(approval.id),
            "estimated_cost_usd": estimated_cost_usd,
        },
    )


async def wait_for_approval(
    db: AsyncSession,
    approval_id: uuid.UUID,
    timeout_seconds: int = 300,
) -> bool:
    """Wait for approval decision (for synchronous workflows).
    
    Args:
        db: Database session
        approval_id: Approval request ID
        timeout_seconds: Maximum time to wait
    
    Returns:
        True if approved, False if rejected or expired
    
    Note:
        This is a blocking operation. For async workflows, use webhooks/events instead.
    """
    import asyncio
    
    service = ApprovalService(db)
    start_time = datetime.now(timezone.utc)
    
    while True:
        query = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await db.execute(query)
        approval = result.scalar_one_or_none()
        
        if not approval:
            return False
        
        if approval.decision == ApprovalDecision.APPROVED:
            return True
        
        if approval.decision in (ApprovalDecision.REJECTED, ApprovalDecision.EXPIRED):
            return False
        
        # Check timeout
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        if elapsed >= timeout_seconds:
            log.warning("approval_wait_timeout", approval_id=str(approval_id))
            return False
        
        # Wait before checking again
        await asyncio.sleep(5)
