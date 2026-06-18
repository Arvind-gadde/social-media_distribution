"""Workspace Insights API — Personalized intelligence feed.

Routes:
  GET    /insights/feed        Get workspace insight feed (unread first)
  GET    /insights/{id}        Get insight details
  PATCH  /insights/{id}/read   Mark insight as read
  PATCH  /insights/{id}/dismiss  Dismiss insight
  POST   /insights/{id}/action   Act on insight (create content from it)
  GET    /insights/stats       Insight statistics
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update, func

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.schemas import WorkspaceInsightResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/feed", response_model=list[WorkspaceInsightResponse])
async def insight_feed(
    workspace: CurrentWorkspace,
    db: DbSession,
    insight_type: str | None = None,
    include_read: bool = False,
    limit: int = 20,
    offset: int = 0,
):
    """Get the workspace insight feed, ordered by priority and recency."""
    from app.domains.intelligence.models import WorkspaceInsight

    stmt = (
        select(WorkspaceInsight)
        .where(
            WorkspaceInsight.workspace_id == workspace.id,
            WorkspaceInsight.is_dismissed == False,
        )
        .order_by(
            WorkspaceInsight.is_read.asc(),
            WorkspaceInsight.priority.asc(),
            WorkspaceInsight.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    if not include_read:
        stmt = stmt.where(WorkspaceInsight.is_read == False)

    if insight_type:
        from app.domains.intelligence.models import InsightType
        try:
            stmt = stmt.where(
                WorkspaceInsight.insight_type == InsightType(insight_type)
            )
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid insight_type: {insight_type}"
            )

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/stats")
async def insight_stats(
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Get insight statistics for the workspace."""
    from app.domains.intelligence.models import WorkspaceInsight

    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(
                WorkspaceInsight.is_read == False
            ).label("unread"),
            func.count().filter(
                WorkspaceInsight.is_actioned == True
            ).label("actioned"),
        )
        .select_from(WorkspaceInsight)
        .where(
            WorkspaceInsight.workspace_id == workspace.id,
            WorkspaceInsight.is_dismissed == False,
        )
    )
    row = result.one()
    return {
        "total": row.total,
        "unread": row.unread,
        "actioned": row.actioned,
    }


@router.get("/{insight_id}", response_model=WorkspaceInsightResponse)
async def get_insight(
    insight_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Get insight details."""
    from app.domains.intelligence.models import WorkspaceInsight

    result = await db.execute(
        select(WorkspaceInsight).where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.patch("/{insight_id}/read", status_code=200)
async def mark_read(
    insight_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Mark an insight as read."""
    from app.domains.intelligence.models import WorkspaceInsight

    result = await db.execute(
        update(WorkspaceInsight)
        .where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
        .values(is_read=True)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"status": "ok"}


@router.patch("/{insight_id}/dismiss", status_code=200)
async def dismiss_insight(
    insight_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Dismiss an insight (hide from feed)."""
    from app.domains.intelligence.models import WorkspaceInsight

    result = await db.execute(
        update(WorkspaceInsight)
        .where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
        .values(is_dismissed=True, is_read=True)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"status": "ok"}


@router.post("/{insight_id}/action", status_code=201)
async def act_on_insight(
    insight_id: uuid.UUID,
    workspace: CurrentWorkspace,
    user: CurrentUser,
    db: DbSession,
):
    """Create a content project from an insight."""
    from app.domains.intelligence.models import WorkspaceInsight
    from app.domains.execution.models import ContentProject, ProjectStatus

    result = await db.execute(
        select(WorkspaceInsight).where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == workspace.id,
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    project = ContentProject(
        workspace_id=workspace.id,
        title=insight.title,
        description=insight.body,
        status=ProjectStatus.IDEA,
        source_insight_id=insight.id,
        created_by=user.id,
    )
    db.add(project)

    # Mark insight as actioned
    await db.execute(
        update(WorkspaceInsight)
        .where(WorkspaceInsight.id == insight_id)
        .values(is_actioned=True, is_read=True)
    )

    await db.flush()
    await db.refresh(project)

    return {
        "status": "ok",
        "project_id": str(project.id),
        "title": project.title,
    }
