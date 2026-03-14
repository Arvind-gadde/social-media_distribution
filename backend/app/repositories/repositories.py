"""Repository layer — all DB access lives here, nowhere else."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Base
from app.models.models import Post, PostStatus, User

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


# ── User Repository ───────────────────────────────────────────────────────

class UserRepository(BaseRepository[User]):
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


# ── Post Repository ───────────────────────────────────────────────────────

class PostRepository(BaseRepository[Post]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Post, session)

    async def get_by_id_str(self, post_id: str) -> Optional[Post]:
        try:
            return await self.get_by_id(uuid.UUID(post_id))
        except ValueError:
            return None

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: Optional[PostStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Post]:
        stmt = (
            select(Post)
            .where(Post.user_id == user_id)
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(Post.status == status)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count()).select_from(Post).where(Post.user_id == user_id)
        )
        return result.scalar_one()

    async def get_platform_stats(self, user_id: uuid.UUID) -> Sequence[Post]:
        """Return all posts for analytics aggregation."""
        result = await self._db.execute(
            select(Post).where(Post.user_id == user_id)
        )
        return result.scalars().all()
