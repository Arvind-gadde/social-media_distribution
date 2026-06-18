"""Trends API - Phase 15.

Exposes trend detection and tracking functionality.
Follows AGENTS.md blueprint section 12 (API Design).
"""
from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.intelligence.models import Trend, TrendStatus, TrendType
from app.domains.execution.models import ContentProject

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/trends", tags=["trends"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class TrendResponse(BaseModel):
    """Trend details."""
    id: uuid.UUID
    niche_id: uuid.UUID | None
    platform: str | None
    trend_type: str
    title: str
    description: str | None
    hashtags: list[str] | None
    example_urls: list[str] | None
    trend_score: float
    trend_velocity: float
    peak_predicted_at: datetime | None
    started_at: datetime | None
    peaked_at: datetime | None
    status: str
    region: str
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrendListResponse(BaseModel):
    """Paginated trends list."""
    items: list[TrendResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CreateContentFromTrendRequest(BaseModel):
    """Create content project from trend."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    content_type: str | None = None
    target_platforms: list[str] | None = None


class CreateContentFromTrendResponse(BaseModel):
    """Created content project."""
    content_project_id: uuid.UUID
    trend_id: uuid.UUID
    title: str
    status: str


# ═══════════════════════════════════════════════════════════════════════════════
# TREND ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=TrendListResponse)
async def list_trends(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TrendStatus | None = Query(None, description="Filter by trend status"),
    trend_type: TrendType | None = Query(None, description="Filter by trend type"),
    platform: str | None = Query(None, description="Filter by platform"),
    niche_id: uuid.UUID | None = Query(None, description="Filter by niche"),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum trend score"),
) -> TrendListResponse:
    """List trends filtered by niche, platform, status, and score.
    
    Returns trends ordered by:
    1. Trend score (descending)
    2. Created date (descending)
    
    Filters:
    - status: rising, peak, declining, dead, evergreen
    - trend_type: hashtag, sound, format, topic, challenge, meme
    - platform: instagram, tiktok, youtube, twitter, etc.
    - niche_id: Filter to workspace's niches
    - min_score: Minimum heat score (0-100)
    """
    # Get workspace niches for filtering
    from app.domains.control.models import WorkspaceNiche
    result = await db.execute(
        select(WorkspaceNiche.niche_id).where(
            WorkspaceNiche.workspace_id == workspace.id
        )
    )
    workspace_niche_ids = [row[0] for row in result.all()]
    
    # Build query
    query = select(Trend).where(
        Trend.trend_score >= min_score,
    )
    
    # Filter by workspace niches if no specific niche requested
    if niche_id:
        query = query.where(Trend.niche_id == niche_id)
    elif workspace_niche_ids:
        query = query.where(
            or_(
                Trend.niche_id.in_(workspace_niche_ids),
                Trend.niche_id.is_(None),  # Global trends
            )
        )
    
    if status:
        query = query.where(Trend.status == status)
    
    if trend_type:
        query = query.where(Trend.trend_type == trend_type)
    
    if platform:
        query = query.where(Trend.platform == platform)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Get paginated results
    query = query.order_by(
        Trend.trend_score.desc(),
        Trend.created_at.desc(),
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    trends = result.scalars().all()
    
    log.info("trends.list",
             workspace_id=str(workspace.id),
             total=total,
             page=page,
             filters={
                 "status": status.value if status else None,
                 "trend_type": trend_type.value if trend_type else None,
                 "platform": platform,
                 "min_score": min_score,
             })
    
    return TrendListResponse(
        items=[TrendResponse.model_validate(t) for t in trends],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> TrendResponse:
    """Get detailed trend information.
    
    Args:
        trend_id: Trend UUID
    
    Returns:
        Trend details including:
        - Heat score and velocity
        - Peak prediction
        - Example content URLs
        - Hashtags
    """
    result = await db.execute(
        select(Trend).where(Trend.id == trend_id)
    )
    trend = result.scalar_one_or_none()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    log.info("trend.get",
             trend_id=str(trend_id),
             workspace_id=str(workspace.id),
             trend_score=trend.trend_score,
             status=trend.status.value)
    
    return TrendResponse.model_validate(trend)


@router.post("/{trend_id}/create-content", response_model=CreateContentFromTrendResponse, status_code=201)
async def create_content_from_trend(
    trend_id: uuid.UUID,
    body: CreateContentFromTrendRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CreateContentFromTrendResponse:
    """Create content project from a trend.
    
    This endpoint:
    1. Validates the trend exists
    2. Creates a new ContentProject linked to the trend
    3. Optionally triggers content ideation agent for suggestions
    
    Args:
        trend_id: Trend to create content from
        body: Content project details
    
    Returns:
        Created content project
    """
    # Get trend
    result = await db.execute(
        select(Trend).where(Trend.id == trend_id)
    )
    trend = result.scalar_one_or_none()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    # Create content project
    content_project = ContentProject(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title=body.title,
        description=body.description or f"Content inspired by trend: {trend.title}",
        content_type=body.content_type,
        niche_id=trend.niche_id,
        target_platforms=body.target_platforms or [trend.platform] if trend.platform else [],
        status="draft",
        source_trend_id=trend_id,
        hashtags=trend.hashtags,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(content_project)
    await db.commit()
    await db.refresh(content_project)
    
    log.info("content.created_from_trend",
             content_project_id=str(content_project.id),
             trend_id=str(trend_id),
             workspace_id=str(workspace.id),
             trend_score=trend.trend_score)
    
    return CreateContentFromTrendResponse(
        content_project_id=content_project.id,
        trend_id=trend_id,
        title=content_project.title,
        status=content_project.status,
    )


@router.get("/stats/summary")
async def get_trend_stats(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> dict:
    """Get trend statistics for workspace.
    
    Returns:
    - Total trends by status
    - Average trend score
    - Trending platforms
    - Hot topics
    """
    # Get workspace niches
    from app.domains.control.models import WorkspaceNiche
    result = await db.execute(
        select(WorkspaceNiche.niche_id).where(
            WorkspaceNiche.workspace_id == workspace.id
        )
    )
    workspace_niche_ids = [row[0] for row in result.all()]
    
    # Get trends for workspace niches
    base_query = select(Trend).where(
        or_(
            Trend.niche_id.in_(workspace_niche_ids) if workspace_niche_ids else False,
            Trend.niche_id.is_(None),
        )
    )
    
    # Count by status
    result = await db.execute(
        select(
            Trend.status,
            func.count(Trend.id).label("count"),
        )
        .where(
            or_(
                Trend.niche_id.in_(workspace_niche_ids) if workspace_niche_ids else False,
                Trend.niche_id.is_(None),
            )
        )
        .group_by(Trend.status)
    )
    status_counts = {row.status.value: row.count for row in result.all()}
    
    # Average trend score
    result = await db.execute(
        select(func.avg(Trend.trend_score))
        .where(
            or_(
                Trend.niche_id.in_(workspace_niche_ids) if workspace_niche_ids else False,
                Trend.niche_id.is_(None),
            ),
            Trend.status.in_([TrendStatus.RISING, TrendStatus.PEAK]),
        )
    )
    avg_score = result.scalar_one() or 0.0
    
    # Top platforms
    result = await db.execute(
        select(
            Trend.platform,
            func.count(Trend.id).label("count"),
        )
        .where(
            or_(
                Trend.niche_id.in_(workspace_niche_ids) if workspace_niche_ids else False,
                Trend.niche_id.is_(None),
            ),
            Trend.status.in_([TrendStatus.RISING, TrendStatus.PEAK]),
            Trend.platform.isnot(None),
        )
        .group_by(Trend.platform)
        .order_by(func.count(Trend.id).desc())
        .limit(5)
    )
    top_platforms = [{"platform": row.platform, "count": row.count} for row in result.all()]
    
    # Hot trends (top 5 by score)
    result = await db.execute(
        select(Trend)
        .where(
            or_(
                Trend.niche_id.in_(workspace_niche_ids) if workspace_niche_ids else False,
                Trend.niche_id.is_(None),
            ),
            Trend.status.in_([TrendStatus.RISING, TrendStatus.PEAK]),
        )
        .order_by(Trend.trend_score.desc())
        .limit(5)
    )
    hot_trends = [
        {
            "id": str(t.id),
            "title": t.title,
            "score": t.trend_score,
            "velocity": t.trend_velocity,
            "platform": t.platform,
        }
        for t in result.scalars().all()
    ]
    
    return {
        "status_counts": status_counts,
        "average_score": round(avg_score, 2),
        "top_platforms": top_platforms,
        "hot_trends": hot_trends,
        "total_active": status_counts.get("rising", 0) + status_counts.get("peak", 0),
    }
