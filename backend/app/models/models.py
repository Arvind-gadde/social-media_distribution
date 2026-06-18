"""Core User model — kept lean. Domain-specific models live in app.domains.

This module exists for backward compatibility with auth and existing imports.
All new models go in app.domains.{control,intelligence,execution}.models.

The old Post, ContentItem, GeneratedPost, AgentRun, ContentInsight models
are superseded by domain models but kept importable for migration reference.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, String, func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Platform identity — a person, not a tenant.

    Users belong to workspaces via WorkspaceMembership.
    A solo creator gets one default workspace on registration.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_id: Mapped[str | None] = mapped_column(
        String(200), unique=True, nullable=True,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(50), default="UTC", nullable=False,
    )
    locale: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # ── MFA / TOTP ───────────────────────────────────────────────────────
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
    )
    mfa_backup_codes: Mapped[list | None] = mapped_column(
        JSON, default=list, nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
