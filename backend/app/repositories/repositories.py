"""Repository layer — all DB access lives here, nowhere else.

Design rules:
  - Every workspace-scoped query MUST accept and filter by workspace_id.
  - Never trust caller-provided IDs without workspace validation.
  - Use select() exclusively — no raw SQL.
  - Repositories are pure data-access. No business logic.
  - Soft-delete aware: exclude deleted_at IS NOT NULL by default.
"""
from __future__ import annotations

import uuid
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Base
from app.models.models import User

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository with basic CRUD."""

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._db = session

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelT]:
        result = await self._db.execute(
            select(self._model).where(self._model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def save(self, record: ModelT) -> ModelT:
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return record

    async def delete_by_id(self, record_id: uuid.UUID) -> None:
        await self._db.execute(
            delete(self._model).where(self._model.id == record_id)
        )
        await self._db.flush()


class WorkspaceScopedRepository(BaseRepository[ModelT]):
    """Repository that enforces workspace-level tenant isolation.

    All queries are automatically scoped to the given workspace_id.
    This is the PRIMARY defense against cross-tenant data leakage.
    """

    def __init__(
        self,
        model: Type[ModelT],
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> None:
        super().__init__(model, session)
        self._workspace_id = workspace_id

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelT]:
        """Get by ID — always scoped to workspace."""
        result = await self._db.execute(
            select(self._model).where(
                self._model.id == record_id,
                self._model.workspace_id == self._workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Sequence[ModelT]:
        """List all records for this workspace with pagination."""
        order_col = getattr(self._model, order_by, self._model.created_at)
        order_expr = order_col.desc() if descending else order_col.asc()
        result = await self._db.execute(
            select(self._model)
            .where(self._model.workspace_id == self._workspace_id)
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """Count records for this workspace."""
        result = await self._db.execute(
            select(func.count())
            .select_from(self._model)
            .where(self._model.workspace_id == self._workspace_id)
        )
        return result.scalar_one()

    async def delete_by_id(self, record_id: uuid.UUID) -> None:
        """Delete — always verifies workspace ownership."""
        await self._db.execute(
            delete(self._model).where(
                self._model.id == record_id,
                self._model.workspace_id == self._workspace_id,
            )
        )
        await self._db.flush()


# ── User Repository ───────────────────────────────────────────────────────


class UserRepository(BaseRepository[User]):
    """User repository — NOT workspace-scoped (users are global)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_id_str(self, user_id: str) -> Optional[User]:
        try:
            return await self.get_by_id(uuid.UUID(user_id))
        except ValueError:
            return None

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()


# ── Workspace Repository ─────────────────────────────────────────────────


class WorkspaceRepository:
    """Workspace CRUD — not scoped (workspaces ARE the scope)."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_by_id(self, workspace_id: uuid.UUID):
        from app.domains.control.models import Workspace
        result = await self._db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str):
        from app.domains.control.models import Workspace
        result = await self._db.execute(
            select(Workspace).where(
                Workspace.slug == slug,
                Workspace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID):
        """All workspaces where user has active membership."""
        from app.domains.control.models import (
            Workspace, WorkspaceMembership, InviteStatus,
        )
        result = await self._db.execute(
            select(Workspace)
            .join(WorkspaceMembership)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.invite_status == InviteStatus.ACTIVE,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at)
        )
        return result.scalars().all()

    async def create(
        self,
        *,
        name: str,
        slug: str,
        owner_id: uuid.UUID,
        timezone: str = "UTC",
    ):
        from app.domains.control.models import (
            Workspace, WorkspaceMembership, WorkspaceRole, InviteStatus,
        )
        from datetime import datetime, timezone as tz

        workspace = Workspace(
            name=name,
            slug=slug,
            owner_id=owner_id,
            timezone=timezone,
        )
        self._db.add(workspace)
        await self._db.flush()

        # Auto-create owner membership
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
            invite_status=InviteStatus.ACTIVE,
            joined_at=datetime.now(tz.utc),
        )
        self._db.add(membership)
        await self._db.flush()
        await self._db.refresh(workspace)
        return workspace


# ── Content Project Repository ──────────────────────────────────────────


class ContentProjectRepository:
    """Content project queries — always workspace-scoped."""

    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id

    async def get_by_id(self, project_id: uuid.UUID):
        from app.domains.execution.models import ContentProject
        result = await self._db.execute(
            select(ContentProject).where(
                ContentProject.id == project_id,
                ContentProject.workspace_id == self._workspace_id,
                ContentProject.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ):
        from app.domains.execution.models import ContentProject
        stmt = (
            select(ContentProject)
            .where(
                ContentProject.workspace_id == self._workspace_id,
                ContentProject.deleted_at.is_(None),
            )
            .order_by(ContentProject.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            from app.domains.execution.models import ProjectStatus
            stmt = stmt.where(ContentProject.status == ProjectStatus(status))
        result = await self._db.execute(stmt)
        return result.scalars().all()


# ── Goal Repository ──────────────────────────────────────────────────────


class GoalRepository:
    """Creator goal queries — always workspace-scoped."""

    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id

    async def get_by_id(self, goal_id: uuid.UUID):
        from app.domains.execution.models import CreatorGoal
        result = await self._db.execute(
            select(CreatorGoal).where(
                CreatorGoal.id == goal_id,
                CreatorGoal.workspace_id == self._workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self):
        from app.domains.execution.models import CreatorGoal, GoalStatus
        result = await self._db.execute(
            select(CreatorGoal).where(
                CreatorGoal.workspace_id == self._workspace_id,
                CreatorGoal.status == GoalStatus.ACTIVE,
            )
            .order_by(CreatorGoal.ends_at.asc())
        )
        return result.scalars().all()

    async def list_all(self, *, limit: int = 50, offset: int = 0):
        from app.domains.execution.models import CreatorGoal
        result = await self._db.execute(
            select(CreatorGoal)
            .where(CreatorGoal.workspace_id == self._workspace_id)
            .order_by(CreatorGoal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


# ── Niche Repository ─────────────────────────────────────────────────────


class NicheRepository:
    """Niche queries — global (niches are shared across workspaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_all(self, *, include_inactive: bool = False):
        from app.domains.control.models import Niche
        stmt = select(Niche).order_by(Niche.sort_order, Niche.name)
        if not include_inactive:
            stmt = stmt.where(Niche.is_active == True)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def list_top_level(self):
        """Only parent niches (no sub-niches)."""
        from app.domains.control.models import Niche
        result = await self._db.execute(
            select(Niche)
            .where(Niche.is_active == True, Niche.parent_niche_id.is_(None))
            .order_by(Niche.sort_order, Niche.name)
        )
        return result.scalars().all()

    async def get_by_slug(self, slug: str):
        from app.domains.control.models import Niche
        result = await self._db.execute(
            select(Niche).where(Niche.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, niche_id: uuid.UUID):
        from app.domains.control.models import Niche
        result = await self._db.execute(
            select(Niche).where(Niche.id == niche_id)
        )
        return result.scalar_one_or_none()

    async def get_children(self, parent_niche_id: uuid.UUID):
        from app.domains.control.models import Niche
        result = await self._db.execute(
            select(Niche)
            .where(
                Niche.parent_niche_id == parent_niche_id,
                Niche.is_active == True,
            )
            .order_by(Niche.sort_order)
        )
        return result.scalars().all()


# ── Source Document Repository ────────────────────────────────────────────


class SourceDocumentRepository:
    """Source document queries — global corpus."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_by_url(self, url: str):
        from app.domains.intelligence.models import SourceDocument
        result = await self._db.execute(
            select(SourceDocument).where(SourceDocument.source_url == url)
        )
        return result.scalar_one_or_none()

    async def list_unprocessed(self, *, limit: int = 40):
        from app.domains.intelligence.models import SourceDocument
        result = await self._db.execute(
            select(SourceDocument)
            .where(SourceDocument.is_processed == False)
            .order_by(SourceDocument.fetched_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_trending(self, *, niche_id: uuid.UUID | None = None, limit: int = 20):
        from app.domains.intelligence.models import SourceDocument
        stmt = (
            select(SourceDocument)
            .where(
                SourceDocument.is_trending == True,
                SourceDocument.is_processed == True,
            )
            .order_by(SourceDocument.relevance_score.desc())
            .limit(limit)
        )
        # If niche filtering is needed, check niche_ids array contains the niche
        result = await self._db.execute(stmt)
        return result.scalars().all()


# ── Workspace Insight Repository ─────────────────────────────────────────


class WorkspaceInsightRepository:
    """Workspace insight queries — always workspace-scoped."""

    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID) -> None:
        self._db = session
        self._workspace_id = workspace_id

    async def list_unread(self, *, limit: int = 20):
        from app.domains.intelligence.models import WorkspaceInsight
        result = await self._db.execute(
            select(WorkspaceInsight)
            .where(
                WorkspaceInsight.workspace_id == self._workspace_id,
                WorkspaceInsight.is_read == False,
                WorkspaceInsight.is_dismissed == False,
            )
            .order_by(
                WorkspaceInsight.priority.asc(),
                WorkspaceInsight.created_at.desc(),
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_read(self, insight_id: uuid.UUID) -> None:
        from app.domains.intelligence.models import WorkspaceInsight
        await self._db.execute(
            update(WorkspaceInsight)
            .where(
                WorkspaceInsight.id == insight_id,
                WorkspaceInsight.workspace_id == self._workspace_id,
            )
            .values(is_read=True)
        )
        await self._db.flush()
