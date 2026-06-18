"""Workspace & Onboarding API — Create workspaces, select niches, complete setup.

Routes:
  POST   /workspaces           Create a new workspace
  GET    /workspaces           List user's workspaces
  GET    /workspaces/current   Get current workspace details
  PATCH  /workspaces/current   Update current workspace
  GET    /niches               List all available niches
  GET    /niches/{slug}        Get niche by slug with children
  POST   /onboarding/niches    Step 2: Select niches for workspace
  POST   /onboarding/goals     Step 4: Set initial goals
  POST   /onboarding/complete  Mark onboarding complete
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser, CurrentWorkspace, DbSession, get_current_user, get_db,
    resolve_workspace,
)
from app.domains.schemas import (
    WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate,
    NicheResponse, WorkspaceNicheSelect, OnboardingStepNiches,
    OnboardingStepGoals, OnboardingComplete, GoalCreate,
)
from app.repositories.repositories import WorkspaceRepository, NicheRepository

router = APIRouter(tags=["workspaces"])


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE CRUD
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Create a new workspace. The authenticated user becomes the owner."""
    repo = WorkspaceRepository(db)

    # Check slug uniqueness
    existing = await repo.get_by_slug(body.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Workspace slug already taken")

    workspace = await repo.create(
        name=body.name,
        slug=body.slug,
        owner_id=user.id,
        timezone=body.timezone,
    )
    return workspace


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: CurrentUser,
    db: DbSession,
):
    """List all workspaces where the user has active membership."""
    repo = WorkspaceRepository(db)
    return await repo.list_for_user(user.id)


@router.get("/workspaces/current", response_model=WorkspaceResponse)
async def get_current_workspace(
    workspace: CurrentWorkspace,
):
    """Get the currently active workspace."""
    return workspace


@router.patch("/workspaces/current", response_model=WorkspaceResponse)
async def update_workspace(
    body: WorkspaceUpdate,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Update the current workspace."""
    from app.domains.control.models import Workspace

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(**update_data)
    )
    await db.flush()
    await db.refresh(workspace)
    return workspace


# ═══════════════════════════════════════════════════════════════════════════════
# NICHES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/niches", response_model=list[NicheResponse])
async def list_niches(
    db: DbSession,
    top_level: bool = True,
):
    """List available niches. Set top_level=false to include sub-niches."""
    repo = NicheRepository(db)
    if top_level:
        return await repo.list_top_level()
    return await repo.list_all()


@router.get("/niches/{slug}", response_model=NicheResponse)
async def get_niche(
    slug: str,
    db: DbSession,
):
    """Get a niche by slug, including children."""
    repo = NicheRepository(db)
    niche = await repo.get_by_slug(slug)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    return niche


# ═══════════════════════════════════════════════════════════════════════════════
# ONBOARDING FLOW
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/onboarding/niches", status_code=200)
async def onboarding_select_niches(
    body: OnboardingStepNiches,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Step 2: Select niches for the workspace."""
    from app.domains.control.models import WorkspaceNiche, Workspace, Niche

    # Validate all niche IDs exist
    for selection in body.niches:
        result = await db.execute(
            select(Niche).where(Niche.id == selection.niche_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail=f"Niche {selection.niche_id} not found",
            )

    # Ensure exactly one primary
    primary_count = sum(1 for n in body.niches if n.is_primary)
    if primary_count == 0:
        body.niches[0].is_primary = True
    elif primary_count > 1:
        raise HTTPException(status_code=400, detail="Only one primary niche allowed")

    # Clear existing niche selections
    from sqlalchemy import delete
    await db.execute(
        delete(WorkspaceNiche).where(
            WorkspaceNiche.workspace_id == workspace.id,
        )
    )

    # Insert new selections
    for selection in body.niches:
        niche_link = WorkspaceNiche(
            workspace_id=workspace.id,
            niche_id=selection.niche_id,
            is_primary=selection.is_primary,
            content_pillars=selection.content_pillars,
            target_audience=selection.target_audience,
        )
        db.add(niche_link)

    # Advance onboarding step
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(onboarding_step=2)
    )
    await db.flush()

    return {"status": "ok", "niches_selected": len(body.niches)}


@router.post("/onboarding/goals", status_code=200)
async def onboarding_set_goals(
    body: OnboardingStepGoals,
    workspace: CurrentWorkspace,
    user: CurrentUser,
    db: DbSession,
):
    """Step 4: Set initial weekly posting goal."""
    from app.domains.execution.models import CreatorGoal, GoalType, GoalPeriod
    from app.domains.control.models import Workspace
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    # Create the weekly posting goal
    goal = CreatorGoal(
        workspace_id=workspace.id,
        title=f"Post {body.weekly_posts_target} times per week",
        description="Weekly content creation goal set during onboarding",
        goal_type=GoalType.CONTENT_COUNT,
        period=GoalPeriod.WEEKLY,
        target_value=float(body.weekly_posts_target),
        unit="posts",
        platform=body.primary_platform,
        starts_at=now,
        ends_at=now + timedelta(weeks=4),
        reminder_enabled=True,
        reminder_schedule={"days": ["monday", "wednesday", "friday"], "time": "09:00"},
    )
    db.add(goal)

    # Create follower goal if specified
    if body.follower_target_monthly and body.follower_target_monthly > 0:
        follower_goal = CreatorGoal(
            workspace_id=workspace.id,
            title=f"Gain {body.follower_target_monthly} followers this month",
            description="Monthly follower growth goal set during onboarding",
            goal_type=GoalType.FOLLOWERS,
            period=GoalPeriod.MONTHLY,
            target_value=float(body.follower_target_monthly),
            unit="followers",
            platform=body.primary_platform,
            starts_at=now,
            ends_at=now + timedelta(days=30),
            reminder_enabled=True,
        )
        db.add(follower_goal)

    # Advance onboarding step
    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(onboarding_step=4)
    )
    await db.flush()

    return {"status": "ok", "goals_created": 1 + (1 if body.follower_target_monthly else 0)}


@router.post("/onboarding/complete", status_code=200)
async def onboarding_complete(
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Mark onboarding as completed."""
    from app.domains.control.models import Workspace

    await db.execute(
        update(Workspace)
        .where(Workspace.id == workspace.id)
        .values(onboarding_completed=True, onboarding_step=5)
    )
    await db.flush()

    return {"status": "ok", "onboarding_completed": True}
