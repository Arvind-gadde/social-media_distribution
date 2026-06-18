"""Collaborations API — CRUD, status, contract management.

Matches the contract that the frontend api-client expects under /collaborations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, WorkspaceCtx
from app.domains.business.models import (
    Collaboration,
    CollaborationStatus,
    CollaborationType,
    ContractDraft,
    ContractStatus,
    PaymentStatus,
)
from app.services.business.contract_drafter import generate_contract

router = APIRouter(prefix="/collaborations", tags=["collaborations"])


class CollaborationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    brand_name: str | None = None
    brand_email: str | None = None
    brand_website: str | None = None
    contact_name: str | None = None
    contact_platform: str | None = None
    contact_handle: str | None = None
    title: str | None = None
    description: str | None = None
    deliverables: list | None = None
    offered_amount: float | None = None
    negotiated_amount: float | None = None
    final_amount: float | None = None
    currency: str
    payment_type: str | None = None
    payment_status: str
    status: str
    ai_score: float | None = None
    ai_recommendation: str | None = None
    source: str | None = None
    source_platform: str | None = None
    deal_starts_at: str | None = None
    deal_ends_at: str | None = None
    deadline_at: str | None = None
    notes: str | None = None
    internal_tags: list[str] | None = None
    metadata: dict | None = None
    created_at: str
    updated_at: str


class PaginatedCollabs(BaseModel):
    items: list[CollaborationOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class CollabCreate(BaseModel):
    type: str = "brand_deal"
    brand_name: str
    brand_email: str | None = None
    contact_name: str | None = None
    title: str | None = None
    description: str | None = None
    offered_amount: float | None = None
    currency: str = "USD"
    status: str | None = None
    deadline_at: datetime | None = None


class CollabUpdate(BaseModel):
    brand_name: str | None = None
    brand_email: str | None = None
    contact_name: str | None = None
    title: str | None = None
    description: str | None = None
    offered_amount: float | None = None
    negotiated_amount: float | None = None
    final_amount: float | None = None
    payment_status: str | None = None
    status: str | None = None
    notes: str | None = None
    deadline_at: datetime | None = None


class StatusUpdate(BaseModel):
    status: str


class ContractOut(BaseModel):
    id: uuid.UUID
    collaboration_id: uuid.UUID
    user_id: uuid.UUID
    contract_type: str
    title: str | None = None
    content: str | None = None
    pdf_url: str | None = None
    status: str
    signed_at: str | None = None
    expires_at: str | None = None
    signature_provider: str | None = None
    external_contract_id: str | None = None
    ai_review_summary: str | None = None
    ai_red_flags: list[str] | None = None
    created_at: str
    updated_at: str


def _to_out(c: Collaboration, user_id: uuid.UUID) -> CollaborationOut:
    return CollaborationOut(
        id=c.id,
        user_id=user_id,
        type=c.collab_type.value,
        brand_name=c.brand_name,
        brand_email=c.brand_email,
        brand_website=c.brand_website,
        contact_name=c.contact_name,
        contact_platform=c.contact_platform,
        contact_handle=c.contact_handle,
        title=c.title,
        description=c.description,
        deliverables=c.deliverables,
        offered_amount=float(c.offered_amount) if c.offered_amount is not None else None,
        negotiated_amount=float(c.negotiated_amount) if c.negotiated_amount is not None else None,
        final_amount=float(c.final_amount) if c.final_amount is not None else None,
        currency=c.currency,
        payment_type=c.payment_type.value if c.payment_type else None,
        payment_status=c.payment_status.value,
        status=c.status.value,
        ai_score=float(c.ai_score) if c.ai_score is not None else None,
        ai_recommendation=c.ai_recommendation,
        source=c.source,
        source_platform=c.source_platform,
        deal_starts_at=c.deal_starts_at.isoformat() if c.deal_starts_at else None,
        deal_ends_at=c.deal_ends_at.isoformat() if c.deal_ends_at else None,
        deadline_at=c.deadline_at.isoformat() if c.deadline_at else None,
        notes=c.notes,
        internal_tags=c.internal_tags,
        metadata=c.metadata_,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_contract_out(c: ContractDraft, user_id: uuid.UUID) -> ContractOut:
    return ContractOut(
        id=c.id,
        collaboration_id=c.collaboration_id,
        user_id=user_id,
        contract_type=getattr(c, "contract_type", "brand_deal"),
        title=c.title,
        content=c.content,
        pdf_url=getattr(c, "pdf_url", None),
        status=c.status.value,
        signed_at=c.signed_at.isoformat() if getattr(c, "signed_at", None) else None,
        expires_at=c.expires_at.isoformat() if getattr(c, "expires_at", None) else None,
        signature_provider=getattr(c, "signature_provider", None),
        external_contract_id=getattr(c, "external_contract_id", None),
        ai_review_summary=getattr(c, "ai_review_summary", None),
        ai_red_flags=getattr(c, "ai_red_flags", None),
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat() if getattr(c, "updated_at", None) else c.created_at.isoformat(),
    )


@router.get("/stats")
async def stats(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> dict[str, Any]:
    total_active = (
        await db.execute(
            select(func.count()).select_from(
                select(Collaboration)
                .where(
                    Collaboration.workspace_id == workspace.id,
                    Collaboration.status.in_(
                        [
                            CollaborationStatus.INQUIRY,
                            CollaborationStatus.NEGOTIATING,
                            CollaborationStatus.CONTRACT_SENT,
                            CollaborationStatus.CONTRACT_SIGNED,
                            CollaborationStatus.IN_PROGRESS,
                        ]
                    ),
                )
                .subquery()
            )
        )
    ).scalar_one()
    total_completed = (
        await db.execute(
            select(func.count()).select_from(
                select(Collaboration)
                .where(
                    Collaboration.workspace_id == workspace.id,
                    Collaboration.status == CollaborationStatus.COMPLETED,
                )
                .subquery()
            )
        )
    ).scalar_one()
    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Collaboration.final_amount), 0)).where(
                Collaboration.workspace_id == workspace.id,
                Collaboration.status == CollaborationStatus.COMPLETED,
            )
        )
    ).scalar_one()

    by_status_rows = (
        await db.execute(
            select(Collaboration.status, func.count())
            .where(Collaboration.workspace_id == workspace.id)
            .group_by(Collaboration.status)
        )
    ).all()
    by_type_rows = (
        await db.execute(
            select(Collaboration.collab_type, func.count())
            .where(Collaboration.workspace_id == workspace.id)
            .group_by(Collaboration.collab_type)
        )
    ).all()

    completed_count = int(total_completed) or 0
    revenue_f = float(revenue or 0)
    avg = (revenue_f / completed_count) if completed_count else 0.0

    return {
        "total_active": int(total_active),
        "total_completed": completed_count,
        "total_revenue": revenue_f,
        "avg_deal_value": avg,
        "by_status": {s.value: int(n) for s, n in by_status_rows},
        "by_type": {t.value: int(n) for t, n in by_type_rows},
    }


@router.get("", response_model=PaginatedCollabs)
async def list_collaborations(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = None,
    type: str | None = None,
    payment_status: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> PaginatedCollabs:
    q = select(Collaboration).where(Collaboration.workspace_id == workspace.id)
    if status:
        try:
            q = q.where(Collaboration.status == CollaborationStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if type:
        try:
            q = q.where(Collaboration.collab_type == CollaborationType(type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
    if payment_status:
        try:
            q = q.where(Collaboration.payment_status == PaymentStatus(payment_status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid payment_status: {payment_status}")
    if min_amount is not None:
        q = q.where(Collaboration.offered_amount >= min_amount)
    if max_amount is not None:
        q = q.where(Collaboration.offered_amount <= max_amount)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Collaboration.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    rows = (await db.execute(q)).scalars().all()
    return PaginatedCollabs(
        items=[_to_out(c, user.id) for c in rows],
        total=int(total),
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < int(total),
    )


@router.post("", response_model=CollaborationOut, status_code=201)
async def create_collaboration(
    body: CollabCreate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CollaborationOut:
    try:
        c_type = CollaborationType(body.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid type: {body.type}")
    try:
        status = CollaborationStatus(body.status) if body.status else CollaborationStatus.INQUIRY
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    collab = Collaboration(
        workspace_id=workspace.id,
        collab_type=c_type,
        status=status,
        brand_name=body.brand_name,
        brand_email=body.brand_email,
        contact_name=body.contact_name,
        title=body.title,
        description=body.description,
        offered_amount=body.offered_amount,
        currency=body.currency or "USD",
        deadline_at=body.deadline_at,
    )
    db.add(collab)
    await db.flush()
    await db.refresh(collab)
    return _to_out(collab, user.id)


async def _load(db, workspace_id: uuid.UUID, collab_id: uuid.UUID) -> Collaboration:
    c = (
        await db.execute(
            select(Collaboration).where(
                Collaboration.id == collab_id,
                Collaboration.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    return c


@router.get("/{collab_id}", response_model=CollaborationOut)
async def get_collaboration(
    collab_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CollaborationOut:
    return _to_out(await _load(db, workspace.id, collab_id), user.id)


@router.patch("/{collab_id}", response_model=CollaborationOut)
async def update_collaboration(
    collab_id: uuid.UUID,
    body: CollabUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CollaborationOut:
    c = await _load(db, workspace.id, collab_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data:
        try:
            data["status"] = CollaborationStatus(data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    if "payment_status" in data:
        try:
            data["payment_status"] = PaymentStatus(data["payment_status"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid payment_status: {data['payment_status']}")
    for k, v in data.items():
        setattr(c, k, v)
    await db.flush()
    await db.refresh(c)
    return _to_out(c, user.id)


@router.patch("/{collab_id}/status", response_model=CollaborationOut)
async def update_status(
    collab_id: uuid.UUID,
    body: StatusUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CollaborationOut:
    c = await _load(db, workspace.id, collab_id)
    try:
        c.status = CollaborationStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    await db.flush()
    await db.refresh(c)
    return _to_out(c, user.id)


@router.delete("/{collab_id}", status_code=204, response_model=None)
async def delete_collaboration(
    collab_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> None:
    c = await _load(db, workspace.id, collab_id)
    await db.delete(c)
    await db.flush()


@router.get("/{collab_id}/contract", response_model=ContractOut)
async def get_contract(
    collab_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContractOut:
    contract = (
        await db.execute(
            select(ContractDraft)
            .where(
                ContractDraft.collaboration_id == collab_id,
                ContractDraft.workspace_id == workspace.id,
            )
            .order_by(ContractDraft.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="No contract for this collaboration")
    return _to_contract_out(contract, user.id)


@router.post("/{collab_id}/contract/generate", response_model=ContractOut, status_code=201)
async def generate_contract_endpoint(
    collab_id: uuid.UUID,
    ctx: WorkspaceCtx,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContractOut:
    await _load(db, workspace.id, collab_id)
    try:
        contract = await generate_contract(db, ctx, collab_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_contract_out(contract, user.id)
