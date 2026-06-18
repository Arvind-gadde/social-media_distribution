"""Competitors API - Phase 15.

Exposes competitor tracking and intelligence functionality.
Follows AGENTS.md blueprint section 12 (API Design).
"""
from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.intelligence.models import CompetitorProfile, CompetitorObservation

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/competitors", tags=["competitors"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class CompetitorCreate(BaseModel):
    """Add competitor to track."""
    platform: str = Field(..., max_length=30, description="Platform (instagram, youtube, tiktok, etc.)")
    platform_username: str = Field(..., max_length=100, description="Username on platform")
    niche_id: uuid.UUID | None = Field(None, description="Niche category")


class CompetitorResponse(BaseModel):
    """Competitor profile details."""
    id: uuid.UUID
    platform: str
    platform_username: str
    display_name: str | None
    avatar_url: str | None
    profile_url: str | None
    niche_id: uuid.UUID | None
    followers_count: int
    avg_engagement_rate: float
    posting_frequency: float
    is_active: bool
    tracking_since: datetime
    last_tracked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    """Paginated competitors list."""
    items: list[CompetitorResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CompetitorObservationResponse(BaseModel):
    """Competitor content observation."""
    id: uuid.UUID
    competitor_id: uuid.UUID
    observation_type: str
    platform_post_id: str | None
    content_type: str | None
    content_summary: str | None
    caption: str | None
    hashtags: list[str] | None
    engagement_metrics: dict | None
    viral_score: float
    ai_analysis: str | None
    content_gaps: list[str] | None
    posted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetitorContentResponse(BaseModel):
    """Competitor content list."""
    items: list[CompetitorObservationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CompetitorAnalysisResponse(BaseModel):
    """AI analysis of competitor strategy."""
    competitor_id: uuid.UUID
    platform: str
    username: str
    
    # Performance metrics
    avg_engagement_rate: float
    posting_frequency: float
    total_posts_tracked: int
    
    # Content analysis
    top_performing_content_types: list[dict]
    common_hashtags: list[str]
    posting_times: dict
    
    # AI insights
    content_strategy_summary: str
    strengths: list[str]
    weaknesses: list[str]
    opportunities_for_you: list[str]
    
    # Trend analysis
    engagement_trend: str  # "increasing", "stable", "decreasing"
    follower_growth_estimate: float


# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = Query(None, description="Filter by platform"),
    niche_id: uuid.UUID | None = Query(None, description="Filter by niche"),
    active_only: bool = Query(True, description="Show only active competitors"),
) -> CompetitorListResponse:
    """List all competitors tracked by workspace.
    
    Returns competitors ordered by:
    1. Average engagement rate (descending)
    2. Followers count (descending)
    """
    # Build query
    query = select(CompetitorProfile).where(
        CompetitorProfile.workspace_id == workspace.id,
    )
    
    if active_only:
        query = query.where(CompetitorProfile.is_active == True)
    
    if platform:
        query = query.where(CompetitorProfile.platform == platform)
    
    if niche_id:
        query = query.where(CompetitorProfile.niche_id == niche_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Get paginated results
    query = query.order_by(
        CompetitorProfile.avg_engagement_rate.desc(),
        CompetitorProfile.followers_count.desc(),
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    competitors = result.scalars().all()
    
    log.info("competitors.list",
             workspace_id=str(workspace.id),
             total=total,
             page=page)
    
    return CompetitorListResponse(
        items=[CompetitorResponse.model_validate(c) for c in competitors],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("", response_model=CompetitorResponse, status_code=201)
async def add_competitor(
    body: CompetitorCreate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CompetitorResponse:
    """Add a new competitor to track.
    
    This will:
    1. Create competitor profile
    2. Trigger initial scrape (async)
    3. Start periodic tracking
    
    Args:
        body: Competitor details
    
    Returns:
        Created competitor profile
    """
    # Check if already tracking
    result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.workspace_id == workspace.id,
            CompetitorProfile.platform == body.platform,
            CompetitorProfile.platform_username == body.platform_username,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=409,
                detail=f"Already tracking {body.platform_username} on {body.platform}"
            )
        else:
            # Reactivate
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
            
            log.info("competitor.reactivated",
                     competitor_id=str(existing.id),
                     workspace_id=str(workspace.id),
                     platform=body.platform,
                     username=body.platform_username)
            
            return CompetitorResponse.model_validate(existing)
    
    # Create new competitor
    competitor = CompetitorProfile(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        platform=body.platform,
        platform_username=body.platform_username,
        niche_id=body.niche_id,
        is_active=True,
        tracking_since=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    
    log.info("competitor.added",
             competitor_id=str(competitor.id),
             workspace_id=str(workspace.id),
             platform=body.platform,
             username=body.platform_username)
    
    # TODO: Trigger competitor intelligence agent to fetch initial data
    
    return CompetitorResponse.model_validate(competitor)


@router.delete("/{competitor_id}", status_code=204, response_model=None)
async def remove_competitor(
    competitor_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> None:
    """Stop tracking a competitor (soft delete).
    
    Args:
        competitor_id: Competitor UUID
    """
    result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.workspace_id == workspace.id,
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor.is_active = False
    await db.commit()
    
    log.info("competitor.removed",
             competitor_id=str(competitor_id),
             workspace_id=str(workspace.id),
             platform=competitor.platform,
             username=competitor.platform_username)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR CONTENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{competitor_id}/content", response_model=CompetitorContentResponse)
async def get_competitor_content(
    competitor_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_viral_score: float = Query(0.0, ge=0.0, le=100.0),
) -> CompetitorContentResponse:
    """Get competitor's tracked content/posts.
    
    Returns observations ordered by:
    1. Viral score (descending)
    2. Posted date (descending)
    
    Args:
        competitor_id: Competitor UUID
        min_viral_score: Filter by minimum viral score
    """
    # Verify competitor belongs to workspace
    result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.workspace_id == workspace.id,
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Build query
    query = select(CompetitorObservation).where(
        CompetitorObservation.competitor_id == competitor_id,
        CompetitorObservation.viral_score >= min_viral_score,
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Get paginated results
    query = query.order_by(
        CompetitorObservation.viral_score.desc(),
        CompetitorObservation.posted_at.desc(),
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    observations = result.scalars().all()
    
    log.info("competitor.content.list",
             competitor_id=str(competitor_id),
             workspace_id=str(workspace.id),
             total=total)
    
    return CompetitorContentResponse(
        items=[CompetitorObservationResponse.model_validate(o) for o in observations],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{competitor_id}/analysis", response_model=CompetitorAnalysisResponse)
async def get_competitor_analysis(
    competitor_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> CompetitorAnalysisResponse:
    """Get AI-powered analysis of competitor strategy.
    
    Analyzes:
    - Content performance patterns
    - Posting strategy
    - Engagement trends
    - Content gaps (opportunities for you)
    
    Args:
        competitor_id: Competitor UUID
    
    Returns:
        Comprehensive competitor intelligence
    """
    # Get competitor
    result = await db.execute(
        select(CompetitorProfile).where(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.workspace_id == workspace.id,
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Get observations for analysis
    result = await db.execute(
        select(CompetitorObservation)
        .where(CompetitorObservation.competitor_id == competitor_id)
        .order_by(CompetitorObservation.created_at.desc())
        .limit(100)
    )
    observations = result.scalars().all()
    
    if not observations:
        raise HTTPException(
            status_code=404,
            detail="No data available yet. Competitor tracking in progress."
        )
    
    # Analyze content types
    content_type_performance = {}
    for obs in observations:
        if obs.content_type and obs.engagement_metrics:
            if obs.content_type not in content_type_performance:
                content_type_performance[obs.content_type] = {
                    "count": 0,
                    "total_engagement": 0.0,
                    "avg_viral_score": 0.0,
                }
            content_type_performance[obs.content_type]["count"] += 1
            content_type_performance[obs.content_type]["total_engagement"] += obs.viral_score
    
    # Calculate averages
    top_content_types = []
    for content_type, stats in content_type_performance.items():
        avg_score = stats["total_engagement"] / stats["count"] if stats["count"] > 0 else 0
        top_content_types.append({
            "type": content_type,
            "count": stats["count"],
            "avg_viral_score": round(avg_score, 2),
        })
    top_content_types.sort(key=lambda x: x["avg_viral_score"], reverse=True)
    
    # Extract common hashtags
    hashtag_freq = {}
    for obs in observations:
        if obs.hashtags:
            for tag in obs.hashtags:
                hashtag_freq[tag] = hashtag_freq.get(tag, 0) + 1
    common_hashtags = sorted(hashtag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    common_hashtags = [tag for tag, _ in common_hashtags]
    
    # Analyze posting times
    posting_hours = {}
    for obs in observations:
        if obs.posted_at:
            hour = obs.posted_at.hour
            posting_hours[hour] = posting_hours.get(hour, 0) + 1
    
    # Determine engagement trend
    if len(observations) >= 10:
        recent_avg = sum(o.viral_score for o in observations[:10]) / 10
        older_avg = sum(o.viral_score for o in observations[-10:]) / 10
        if recent_avg > older_avg * 1.1:
            engagement_trend = "increasing"
        elif recent_avg < older_avg * 0.9:
            engagement_trend = "decreasing"
        else:
            engagement_trend = "stable"
    else:
        engagement_trend = "insufficient_data"
    
    # Generate AI insights (simplified - in production, use LLM)
    strengths = []
    weaknesses = []
    opportunities = []
    
    if top_content_types:
        best_type = top_content_types[0]
        strengths.append(f"Strong performance with {best_type['type']} content (avg score: {best_type['avg_viral_score']})")
    
    if competitor.avg_engagement_rate > 5.0:
        strengths.append(f"High engagement rate ({competitor.avg_engagement_rate:.1f}%)")
    elif competitor.avg_engagement_rate < 2.0:
        weaknesses.append(f"Low engagement rate ({competitor.avg_engagement_rate:.1f}%)")
    
    if competitor.posting_frequency < 3.0:
        weaknesses.append(f"Inconsistent posting ({competitor.posting_frequency:.1f} posts/week)")
        opportunities.append("Opportunity to outpace with consistent posting schedule")
    
    # Identify content gaps
    content_gaps = []
    for obs in observations:
        if obs.content_gaps:
            content_gaps.extend(obs.content_gaps)
    unique_gaps = list(set(content_gaps))[:5]
    
    for gap in unique_gaps:
        opportunities.append(f"Content gap: {gap}")
    
    strategy_summary = (
        f"{competitor.platform_username} posts {competitor.posting_frequency:.1f} times per week "
        f"with an average engagement rate of {competitor.avg_engagement_rate:.1f}%. "
        f"Their best performing content type is {top_content_types[0]['type'] if top_content_types else 'unknown'}. "
        f"Engagement trend: {engagement_trend}."
    )
    
    log.info("competitor.analysis",
             competitor_id=str(competitor_id),
             workspace_id=str(workspace.id),
             observations_analyzed=len(observations))
    
    return CompetitorAnalysisResponse(
        competitor_id=competitor_id,
        platform=competitor.platform,
        username=competitor.platform_username,
        avg_engagement_rate=competitor.avg_engagement_rate,
        posting_frequency=competitor.posting_frequency,
        total_posts_tracked=len(observations),
        top_performing_content_types=top_content_types[:5],
        common_hashtags=common_hashtags,
        posting_times=posting_hours,
        content_strategy_summary=strategy_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        opportunities_for_you=opportunities,
        engagement_trend=engagement_trend,
        follower_growth_estimate=0.0,  # TODO: Calculate from historical data
    )
