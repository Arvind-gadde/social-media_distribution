"""Database session management."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

_IS_CELERY_WORKER = os.getenv("CELERY_WORKER") == "1"

# SQLite doesn't support pool_size/max_overflow
if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG,
    )
elif _IS_CELERY_WORKER:
    # Celery runs asyncio.run() per task → new loop each call.
    # NullPool avoids reusing asyncpg cxns tied to a dead loop.
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency — yields a DB session, commits on success, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
