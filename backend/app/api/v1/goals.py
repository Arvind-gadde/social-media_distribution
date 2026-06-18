"""Goals API - Phase 15.

Exposes goal tracking and accountability functionality.
Follows AGENTS.md blueprint section 12 (API Design).
"""
from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.execution.models import CreatorGoal as Goal, GoalCheckIn

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/goals", tags=["goals"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class GoalCreate(BaseModel):
    """Create new goal."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    goal_type: str = Field(..., description="content_count, followers, views, revenue, engagement")
    period: str = Field(..., description="daily, weekly, monthly, quarterly, yearly")
    target_value: float = Field(..., gt=0)
    unit: str = Field(..., description="posts, followers, views, dollars")
    platform: str | None = Field(None, description="Specific platform or null for all")
    starts_at: datetime
    ends_at: datetime
    reminder_enabled: bool = True
    reminder_schedule: dict | None = Field(None, description='{"days": ["monday"], "time": "09:00"}')


class GoalUpdate(BaseModel):
    """Update goal."""
    title: str | None = None
    description: str | None = None
    target_value: float | None = Field(None, gt=0)
    status: str | None = Field(None, description="active, paused, completed, failed, archived")
    reminder_enabled: bool | None = None
    reminder_schedule: dict | None = None


class GoalResponse(BaseModel):
    """Goal details."""
    id: uuid.UUID
    title: str
    description: str | None
    goal_type: str
    period: str
    target_value: float
    current_value: float
    unit: str
    platform: str | None
    status: str
    starts_at: datetime
    ends_at: datetime
    reminder_enabled: bool
    reminder_schedule: dict | None
    completed_at: datetime | None
    streak_count: int
    best_streak: int
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    progress_pct: float
    days_remaining: int
    is_on_track: bool

    model_config = {"from_attributes": True}

    @staticmethod
    def from_orm_with_computed(goal: Goal) -> "GoalResponse":
        """Create response with computed fields."""
        progress_pct = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0.0
        progress_pct = min(round(progress_pct, 1), 100.0)
        
        days_remaining = (goal.ends_at - datetime.now(timezone.utc)).days
        days_remaining = max(days_remaining, 0)
        
        # Calculate if on track
        total_days = (goal.ends_at - goal.starts_at).days
        elapsed_days = (datetime.now(timezone.utc) - goal.starts_at).days
        expected_progress = (elapsed_days / total_days * 100) if total_days > 0 else 0
        is_on_track = progress_pct >= expected_progress * 0.9  # 90% of expected
        
        return GoalResponse(
            id=goal.id,
            title=goal.title,
            description=goal.description,
            goal_type=goal.goal_type,
            period=goal.period,
            target_value=goal.target_value,
            current_value=goal.current_value,
            unit=goal.unit,
            platform=goal.platform,
            status=goal.status,
            starts_at=goal.starts_at,
            ends_at=goal.ends_at,
            reminder_enabled=goal.reminder_enabled,
            reminder_schedule=goal.reminder_schedule,
            completed_at=goal.completed_at,
            streak_count=goal.streak_count,
            best_streak=goal.best_streak,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
            progress_pct=progress_pct,
            days_remaining=days_remaining,
            is_on_track=is_on_track,
        )


class GoalListResponse(BaseModel):
    """Paginated goals list."""
    items: list[GoalResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class GoalCheckInCreate(BaseModel):
    """Manual goal check-in."""
    value_at_checkin: float = Field(..., ge=0)
    note: str | None = None


class GoalCheckInResponse(BaseModel):
    """Goal check-in details."""
    id: uuid.UUID
    goal_id: uuid.UUID
    value_at_checkin: float
    progress_pct: float
    note: str | None
    agent_analysis: str | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class GoalHistoryResponse(BaseModel):
    """Goal progress history."""
    goal_id: uuid.UUID
    check_ins: list[GoalCheckInResponse]
    total_check_ins: int


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=GoalListResponse)
async def list_goals(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status"),
    goal_type: str | None = Query(None, description="Filter by goal type"),
    platform: str | None = Query(None, description="Filter by platform"),
) -> GoalListResponse:
    """List all goals for workspace.
    
    Returns goals ordered by:
    1. Status (active first)
    2. End date (soonest first)
    """
    # Build query
    query = select(Goal).where(
        Goal.workspace_id == workspace.id,
    )
    
    if status:
        query = query.where(Goal.status == status)
    
    if goal_type:
        query = query.where(Goal.goal_type == goal_type)
    
    if platform:
        query = query.where(Goal.platform == platform)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Get paginated results
    query = query.order_by(
        Goal.status.asc(),  # active first
        Goal.ends_at.asc(),  # soonest deadline first
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    goals = result.scalars().all()
    
    log.info("goals.list",
             workspace_id=str(workspace.id),
             total=total,
             page=page)
    
    return GoalListResponse(
        items=[GoalResponse.from_orm_with_computed(g) for g in goals],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    body: GoalCreate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> GoalResponse:
    """Create a new goal.
    
    Args:
        body: Goal details
    
    Returns:
        Created goal
    """
    # Validate dates
    if body.ends_at <= body.starts_at:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    # Create goal
    goal = Goal(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title=body.title,
        description=body.description,
        goal_type=body.goal_type,
        period=body.period,
        target_value=body.target_value,
        current_value=0.0,
        unit=body.unit,
        platform=body.platform,
        status="active",
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        reminder_enabled=body.reminder_enabled,
        reminder_schedule=body.reminder_schedule,
        streak_count=0,
        best_streak=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    
    log.info("goal.created",
             goal_id=str(goal.id),
             workspace_id=str(workspace.id),
             goal_type=body.goal_type,
             target=body.target_value)
    
    return GoalResponse.from_orm_with_computed(goal)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> GoalResponse:
    """Get goal details.
    
    Args:
        goal_id: Goal UUID
    
    Returns:
        Goal details with computed progress
    """
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.workspace_id == workspace.id,
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return GoalResponse.from_orm_with_computed(goal)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    body: GoalUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> GoalResponse:
    """Update goal details.
    
    Args:
        goal_id: Goal UUID
        body: Fields to update
    
    Returns:
        Updated goal
    """
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.workspace_id == workspace.id,
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Update fields
    if body.title is not None:
        goal.title = body.title
    if body.description is not None:
        goal.description = body.description
    if body.target_value is not None:
        goal.target_value = body.target_value
    if body.status is not None:
        goal.status = body.status
        if body.status == "completed" and not goal.completed_at:
            goal.completed_at = datetime.now(timezone.utc)
    if body.reminder_enabled is not None:
        goal.reminder_enabled = body.reminder_enabled
    if body.reminder_schedule is not None:
        goal.reminder_schedule = body.reminder_schedule
    
    goal.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(goal)
    
    log.info("goal.updated",
             goal_id=str(goal_id),
             workspace_id=str(workspace.id),
             updates=body.model_dump(exclude_none=True))
    
    return GoalResponse.from_orm_with_computed(goal)


@router.delete("/{goal_id}", status_code=204, response_model=None)
async def delete_goal(
    goal_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> None:
    """Delete a goal.
    
    Args:
        goal_id: Goal UUID
    """
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.workspace_id == workspace.id,
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    await db.delete(goal)
    await db.commit()
    
    log.info("goal.deleted",
             goal_id=str(goal_id),
             workspace_id=str(workspace.id))


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL PROGRESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{goal_id}/check-in", response_model=GoalCheckInResponse, status_code=201)
async def create_check_in(
    goal_id: uuid.UUID,
    body: GoalCheckInCreate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> GoalCheckInResponse:
    """Manual goal progress check-in.
    
    Updates goal's current_value and creates check-in record.
    
    Args:
        goal_id: Goal UUID
        body: Check-in details
    
    Returns:
        Created check-in
    """
    # Get goal
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.workspace_id == workspace.id,
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Update goal current value
    goal.current_value = body.value_at_checkin
    goal.updated_at = datetime.now(timezone.utc)
    
    # Check if goal completed
    if body.value_at_checkin >= goal.target_value and goal.status == "active":
        goal.status = "completed"
        goal.completed_at = datetime.now(timezone.utc)
    
    # Calculate progress
    progress_pct = (body.value_at_checkin / goal.target_value * 100) if goal.target_value > 0 else 0.0
    progress_pct = min(round(progress_pct, 2), 100.0)
    
    # Create check-in
    check_in = GoalCheckIn(
        id=uuid.uuid4(),
        goal_id=goal_id,
        value_at_checkin=body.value_at_checkin,
        progress_pct=progress_pct,
        note=body.note,
        checked_at=datetime.now(timezone.utc),
    )
    
    db.add(check_in)
    await db.commit()
    await db.refresh(check_in)
    
    log.info("goal.check_in",
             goal_id=str(goal_id),
             workspace_id=str(workspace.id),
             value=body.value_at_checkin,
             progress_pct=progress_pct)
    
    return GoalCheckInResponse.model_validate(check_in)


@router.get("/{goal_id}/history", response_model=GoalHistoryResponse)
async def get_goal_history(
    goal_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
) -> GoalHistoryResponse:
    """Get goal progress history.
    
    Args:
        goal_id: Goal UUID
        limit: Max check-ins to return
    
    Returns:
        Check-in history ordered by date (newest first)
    """
    # Verify goal exists
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.workspace_id == workspace.id,
        )
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Get check-ins
    result = await db.execute(
        select(GoalCheckIn)
        .where(GoalCheckIn.goal_id == goal_id)
        .order_by(GoalCheckIn.checked_at.desc())
        .limit(limit)
    )
    check_ins = result.scalars().all()
    
    # Get total count
    result = await db.execute(
        select(func.count(GoalCheckIn.id))
        .where(GoalCheckIn.goal_id == goal_id)
    )
    total = result.scalar_one()
    
    log.info("goal.history",
             goal_id=str(goal_id),
             workspace_id=str(workspace.id),
             check_ins=len(check_ins))
    
    return GoalHistoryResponse(
        goal_id=goal_id,
        check_ins=[GoalCheckInResponse.model_validate(c) for c in check_ins],
        total_check_ins=total,
    )
