"""Business API — DM Inbox, Collaborations, Contracts.

Endpoints for managing creator business operations:
- DM inbox with AI classification
- Deal pipeline (Kanban view)
- Contract generation
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.domains.business.models import (
    Collaboration, CollaborationStatus, ContractDraft, DMCategory, DMInbox,
)
from app.models.models import User
from app.runtime.context import RunContext
from app.services.business.collab_evaluator import evaluate_unread_dms
from app.services.business.contract_drafter import generate_contract
from app.services.business.inbox_sync import sync_workspace_dms

router = APIRouter(prefix="/business", tags=["business"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class DMInboxResponse(BaseModel):
    id: uuid.UUID
    platform: str
    sender_username: str
    sender_display_name: str | None
    sender_followers_count: int | None
    message_text: str
    is_business_inquiry: bool
    ai_category: str | None
    ai_priority: int
    ai_summary: str | None
    ai_suggested_reply: str | None
    is_read: bool
    collaboration_id: uuid.UUID | None
    received_at: str

    class Config:
        from_attributes = True


class CollaborationResponse(BaseModel):
    id: uuid.UUID
    collab_type: str
    status: str
    brand_name: str
    contact_handle: str | None
    title: str | None
    deliverables: list | None
    offered_amount: float | None
    final_amount: float | None
    currency: str
    ai_score: float | None
    ai_recommendation: str | None
    created_at: str

    class Config:
        from_attributes = True


class ContractResponse(BaseModel):
    id: uuid.UUID
    collaboration_id: uuid.UUID
    title: str | None
    content: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class GenerateContractRequest(BaseModel):
    collaboration_id: uuid.UUID = Field(..., description="Collaboration ID to generate contract for")


class PipelineResponse(BaseModel):
    """Kanban-style pipeline view."""
    inquiry: list[CollaborationResponse]
    negotiating: list[CollaborationResponse]
    contract_sent: list[CollaborationResponse]
    in_progress: list[CollaborationResponse]
    completed: list[CollaborationResponse]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/inbox", response_model=list[DMInboxResponse])
async def get_dm_inbox(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    category: Annotated[DMCategory | None, Query()] = None,
    is_read: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Get DM inbox with optional filters.
    
    Filters:
    - category: Filter by AI category (brand_deal, collab, fan, spam, etc.)
    - is_read: Filter by read status
    """
    query = select(DMInbox).where(
        DMInbox.workspace_id == current_user.workspace_id,
    )
    
    if category:
        query = query.where(DMInbox.ai_category == category)
    if is_read is not None:
        query = query.where(DMInbox.is_read == is_read)
    
    query = query.order_by(
        DMInbox.ai_priority.desc(),
        DMInbox.received_at.desc(),
    ).limit(limit).offset(offset)
    
    result = await db.execute(query)
    dms = result.scalars().all()
    
    return [
        DMInboxResponse(
            id=dm.id,
            platform=dm.platform,
            sender_username=dm.sender_username,
            sender_display_name=dm.sender_display_name,
            sender_followers_count=dm.sender_followers_count,
            message_text=dm.message_text,
            is_business_inquiry=dm.is_business_inquiry,
            ai_category=dm.ai_category.value if dm.ai_category else None,
            ai_priority=dm.ai_priority,
            ai_summary=dm.ai_summary,
            ai_suggested_reply=dm.ai_suggested_reply,
            is_read=dm.is_read,
            collaboration_id=dm.collaboration_id,
            received_at=dm.received_at.isoformat(),
        )
        for dm in dms
    ]


@router.patch("/inbox/{dm_id}/read")
async def mark_dm_read(
    dm_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Mark DM as read."""
    result = await db.execute(
        select(DMInbox).where(
            DMInbox.id == dm_id,
            DMInbox.workspace_id == current_user.workspace_id,
        )
    )
    dm = result.scalar_one_or_none()
    
    if not dm:
        raise HTTPException(status_code=404, detail="DM not found")
    
    dm.is_read = True
    await db.commit()
    
    return {"status": "success"}


@router.post("/inbox/sync")
async def sync_inbox(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Manually trigger DM sync for workspace."""
    ctx = RunContext(
        workspace_id=current_user.workspace_id,
        actor_id=str(current_user.id),
        trigger="manual",
        correlation_id=str(uuid.uuid4()),
    )
    
    stats = await sync_workspace_dms(db, ctx)
    return stats


@router.post("/inbox/evaluate")
async def evaluate_inbox(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Manually trigger AI evaluation of unread DMs."""
    ctx = RunContext(
        workspace_id=current_user.workspace_id,
        actor_id=str(current_user.id),
        trigger="manual",
        correlation_id=str(uuid.uuid4()),
    )
    
    stats = await evaluate_unread_dms(db, ctx)
    return stats


@router.get("/pipeline", response_model=PipelineResponse)
async def get_pipeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get Kanban-style pipeline view of all collaborations."""
    result = await db.execute(
        select(Collaboration).where(
            Collaboration.workspace_id == current_user.workspace_id,
        ).order_by(Collaboration.created_at.desc())
    )
    collabs = result.scalars().all()
    
    # Group by status
    pipeline = {
        "inquiry": [],
        "negotiating": [],
        "contract_sent": [],
        "in_progress": [],
        "completed": [],
    }
    
    for collab in collabs:
        response = CollaborationResponse(
            id=collab.id,
            collab_type=collab.collab_type.value,
            status=collab.status.value,
            brand_name=collab.brand_name,
            contact_handle=collab.contact_handle,
            title=collab.title,
            deliverables=collab.deliverables,
            offered_amount=float(collab.offered_amount) if collab.offered_amount else None,
            final_amount=float(collab.final_amount) if collab.final_amount else None,
            currency=collab.currency,
            ai_score=float(collab.ai_score) if collab.ai_score else None,
            ai_recommendation=collab.ai_recommendation,
            created_at=collab.created_at.isoformat(),
        )
        
        if collab.status == CollaborationStatus.INQUIRY:
            pipeline["inquiry"].append(response)
        elif collab.status == CollaborationStatus.NEGOTIATING:
            pipeline["negotiating"].append(response)
        elif collab.status == CollaborationStatus.CONTRACT_SENT:
            pipeline["contract_sent"].append(response)
        elif collab.status == CollaborationStatus.IN_PROGRESS:
            pipeline["in_progress"].append(response)
        elif collab.status == CollaborationStatus.COMPLETED:
            pipeline["completed"].append(response)
    
    return PipelineResponse(**pipeline)


@router.get("/collaborations/{collab_id}", response_model=CollaborationResponse)
async def get_collaboration(
    collab_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get collaboration details."""
    result = await db.execute(
        select(Collaboration).where(
            Collaboration.id == collab_id,
            Collaboration.workspace_id == current_user.workspace_id,
        )
    )
    collab = result.scalar_one_or_none()
    
    if not collab:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    
    return CollaborationResponse(
        id=collab.id,
        collab_type=collab.collab_type.value,
        status=collab.status.value,
        brand_name=collab.brand_name,
        contact_handle=collab.contact_handle,
        title=collab.title,
        deliverables=collab.deliverables,
        offered_amount=float(collab.offered_amount) if collab.offered_amount else None,
        final_amount=float(collab.final_amount) if collab.final_amount else None,
        currency=collab.currency,
        ai_score=float(collab.ai_score) if collab.ai_score else None,
        ai_recommendation=collab.ai_recommendation,
        created_at=collab.created_at.isoformat(),
    )


@router.post("/collaborations/{collab_id}/generate-contract", response_model=ContractResponse)
async def generate_contract_endpoint(
    collab_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Generate AI contract draft for collaboration."""
    ctx = RunContext(
        workspace_id=current_user.workspace_id,
        actor_id=str(current_user.id),
        trigger="manual",
        correlation_id=str(uuid.uuid4()),
    )
    
    try:
        contract = await generate_contract(db, ctx, collab_id)
        
        return ContractResponse(
            id=contract.id,
            collaboration_id=contract.collaboration_id,
            title=contract.title,
            content=contract.content,
            status=contract.status.value,
            created_at=contract.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get contract details."""
    result = await db.execute(
        select(ContractDraft).where(
            ContractDraft.id == contract_id,
            ContractDraft.workspace_id == current_user.workspace_id,
        )
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return ContractResponse(
        id=contract.id,
        collaboration_id=contract.collaboration_id,
        title=contract.title,
        content=contract.content,
        status=contract.status.value,
        created_at=contract.created_at.isoformat(),
    )
