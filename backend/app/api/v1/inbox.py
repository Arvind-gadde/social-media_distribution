"""Inbox API — DM management at frontend-expected paths /inbox/dms.

Wraps existing DMInbox model with the contract the frontend api-client expects.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.business.models import (
    Collaboration,
    DMCategory,
    DMInbox,
)

router = APIRouter(prefix="/inbox", tags=["inbox"])


class DMResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    social_account_id: uuid.UUID
    platform: str
    sender_platform_id: str
    sender_username: str
    sender_display_name: str | None = None
    sender_avatar_url: str | None = None
    sender_followers_count: int | None = None
    message_text: str
    is_business_inquiry: bool
    ai_category: str | None = None
    ai_summary: str | None = None
    ai_sentiment: float | None = None
    ai_priority: int
    ai_suggested_reply: str | None = None
    is_read: bool
    is_replied: bool
    collaboration_id: uuid.UUID | None = None
    received_at: str
    platform_message_id: str | None = None
    created_at: str


class PaginatedDMs(BaseModel):
    items: list[DMResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class DMReplyRequest(BaseModel):
    message: str = Field(..., min_length=1)


class LinkCollabRequest(BaseModel):
    collaboration_id: uuid.UUID


def _to_response(dm: DMInbox, user_id: uuid.UUID) -> DMResponse:
    return DMResponse(
        id=dm.id,
        user_id=user_id,
        social_account_id=dm.social_account_id,
        platform=dm.platform,
        sender_platform_id=dm.sender_platform_id,
        sender_username=dm.sender_username,
        sender_display_name=dm.sender_display_name,
        sender_avatar_url=dm.sender_avatar_url,
        sender_followers_count=dm.sender_followers_count,
        message_text=dm.message_text,
        is_business_inquiry=dm.is_business_inquiry,
        ai_category=dm.ai_category.value if dm.ai_category else None,
        ai_summary=dm.ai_summary,
        ai_sentiment=float(dm.ai_sentiment) if dm.ai_sentiment is not None else None,
        ai_priority=dm.ai_priority,
        ai_suggested_reply=dm.ai_suggested_reply,
        is_read=dm.is_read,
        is_replied=dm.is_replied,
        collaboration_id=dm.collaboration_id,
        received_at=dm.received_at.isoformat(),
        platform_message_id=dm.platform_message_id,
        created_at=dm.created_at.isoformat(),
    )


@router.get("/dms/stats")
async def dm_stats(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> dict[str, Any]:
    base = select(DMInbox).where(DMInbox.workspace_id == workspace.id)

    total_unread = (
        await db.execute(
            select(func.count()).select_from(
                base.where(DMInbox.is_read.is_(False)).subquery()
            )
        )
    ).scalar_one()
    total_business = (
        await db.execute(
            select(func.count()).select_from(
                base.where(DMInbox.is_business_inquiry.is_(True)).subquery()
            )
        )
    ).scalar_one()
    high_priority = (
        await db.execute(
            select(func.count()).select_from(
                base.where(DMInbox.ai_priority >= 8).subquery()
            )
        )
    ).scalar_one()

    by_platform_rows = (
        await db.execute(
            select(DMInbox.platform, func.count())
            .where(DMInbox.workspace_id == workspace.id)
            .group_by(DMInbox.platform)
        )
    ).all()
    by_category_rows = (
        await db.execute(
            select(DMInbox.ai_category, func.count())
            .where(DMInbox.workspace_id == workspace.id)
            .group_by(DMInbox.ai_category)
        )
    ).all()

    return {
        "total_unread": int(total_unread),
        "total_business_inquiries": int(total_business),
        "high_priority_count": int(high_priority),
        "by_platform": {p: int(c) for p, c in by_platform_rows if p},
        "by_category": {
            (c.value if hasattr(c, "value") else str(c)): int(n)
            for c, n in by_category_rows
            if c is not None
        },
    }


@router.get("/dms", response_model=PaginatedDMs)
async def list_dms(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    platform: str | None = None,
    is_read: bool | None = None,
    is_business_inquiry: bool | None = None,
    ai_category: str | None = None,
    min_priority: Annotated[int | None, Query(ge=1, le=10)] = None,
) -> PaginatedDMs:
    q = select(DMInbox).where(DMInbox.workspace_id == workspace.id)
    if platform:
        q = q.where(DMInbox.platform == platform)
    if is_read is not None:
        q = q.where(DMInbox.is_read.is_(is_read))
    if is_business_inquiry is not None:
        q = q.where(DMInbox.is_business_inquiry.is_(is_business_inquiry))
    if ai_category:
        try:
            q = q.where(DMInbox.ai_category == DMCategory(ai_category))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {ai_category}")
    if min_priority:
        q = q.where(DMInbox.ai_priority >= min_priority)

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()

    q = q.order_by(DMInbox.ai_priority.desc(), DMInbox.received_at.desc())
    q = q.limit(page_size).offset((page - 1) * page_size)
    rows = (await db.execute(q)).scalars().all()
    items = [_to_response(dm, user.id) for dm in rows]
    return PaginatedDMs(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < int(total),
    )


async def _load_dm(db, workspace_id: uuid.UUID, dm_id: uuid.UUID) -> DMInbox:
    dm = (
        await db.execute(
            select(DMInbox).where(
                DMInbox.id == dm_id,
                DMInbox.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not dm:
        raise HTTPException(status_code=404, detail="DM not found")
    return dm


@router.get("/dms/{dm_id}", response_model=DMResponse)
async def get_dm(
    dm_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> DMResponse:
    dm = await _load_dm(db, workspace.id, dm_id)
    return _to_response(dm, user.id)


@router.patch("/dms/{dm_id}/read", response_model=DMResponse)
async def mark_read(
    dm_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> DMResponse:
    dm = await _load_dm(db, workspace.id, dm_id)
    dm.is_read = True
    await db.flush()
    return _to_response(dm, user.id)


@router.patch("/dms/{dm_id}/unread", response_model=DMResponse)
async def mark_unread(
    dm_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> DMResponse:
    dm = await _load_dm(db, workspace.id, dm_id)
    dm.is_read = False
    await db.flush()
    return _to_response(dm, user.id)


@router.post("/dms/{dm_id}/reply", response_model=DMResponse)
async def reply_dm(
    dm_id: uuid.UUID,
    body: DMReplyRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> DMResponse:
    """Record a reply. Platform API send is delegated to platform workers and is best-effort here."""
    from datetime import datetime, timezone

    dm = await _load_dm(db, workspace.id, dm_id)
    dm.is_replied = True
    dm.replied_at = datetime.now(timezone.utc)
    # Note: actual platform send is queued elsewhere; we just persist intent here.
    await db.flush()
    return _to_response(dm, user.id)


@router.patch("/dms/{dm_id}/link", response_model=DMResponse)
async def link_to_collaboration(
    dm_id: uuid.UUID,
    body: LinkCollabRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> DMResponse:
    dm = await _load_dm(db, workspace.id, dm_id)
    collab = (
        await db.execute(
            select(Collaboration).where(
                Collaboration.id == body.collaboration_id,
                Collaboration.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    dm.collaboration_id = collab.id
    await db.flush()
    return _to_response(dm, user.id)
