"""Workspace niche resolver — resolves the primary niche for a workspace.

Used by the orchestrator and niche adapter to determine which
niche prompt overrides and source configurations to use.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import WorkspaceNiche, Niche


async def get_primary_niche_slug(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> str | None:
    """Resolve the primary niche slug for a workspace.

    Returns the slug of the primary niche, or the first niche
    if none is marked as primary, or None if no niche is set.
    """
    result = await db.execute(
        select(Niche.slug)
        .join(WorkspaceNiche, WorkspaceNiche.niche_id == Niche.id)
        .where(
            WorkspaceNiche.workspace_id == workspace_id,
            WorkspaceNiche.is_primary == True,
        )
        .limit(1)
    )
    slug = result.scalar_one_or_none()
    if slug:
        return slug

    # Fallback: first niche for this workspace
    result = await db.execute(
        select(Niche.slug)
        .join(WorkspaceNiche, WorkspaceNiche.niche_id == Niche.id)
        .where(WorkspaceNiche.workspace_id == workspace_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_workspace_niche_slugs(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[str]:
    """Return all niche slugs for a workspace, primary first."""
    result = await db.execute(
        select(Niche.slug, WorkspaceNiche.is_primary)
        .join(WorkspaceNiche, WorkspaceNiche.niche_id == Niche.id)
        .where(WorkspaceNiche.workspace_id == workspace_id)
        .order_by(WorkspaceNiche.is_primary.desc())
    )
    return [row[0] for row in result.all()]
