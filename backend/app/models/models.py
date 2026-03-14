"""ORM models — User and Post."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── User ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Google OAuth — null for email/password users
    google_id: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)

    # Email/password auth — null for Google-only users
    # Stored as bcrypt hash — NEVER store plaintext passwords
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    # Encrypted platform OAuth tokens — NEVER store plaintext here.
    # Shape after decryption: {"instagram": {"access_token": "...", "user_id": "..."}, ...}
    encrypted_platform_tokens: Mapped[dict | None] = mapped_column(
        JSON, default=dict, nullable=True
    )
    connected_platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user", lazy="select")


# ── Post ──────────────────────────────────────────────────────────────────

class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    PUBLISHED = "published"
    PARTIAL = "partial"   # some platforms succeeded
    FAILED = "failed"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Media
    media_key: Mapped[str | None] = mapped_column(String(500), nullable=True)   # R2/S3 key
    media_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # Public URL
    media_type: Mapped[str | None] = mapped_column(String(20), nullable=True)   # image/video/text
    media_duration_s: Mapped[float | None] = mapped_column(nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Distribution
    target_platforms: Mapped[list] = mapped_column(JSON, default=list)
    # platform_status: {"instagram": "published", "youtube": "failed:api_error"}
    platform_status: Mapped[dict] = mapped_column(JSON, default=dict)
    # platform_content: {"instagram": {"caption": "...", "hashtags": [...]}}
    platform_content: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_platforms: Mapped[list] = mapped_column(JSON, default=list)

    # Lifecycle
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, native_enum=False),
        default=PostStatus.DRAFT,
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="posts")