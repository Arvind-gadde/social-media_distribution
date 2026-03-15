"""ORM models — User, Post, ContentItem, GeneratedPost."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Index, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now())
    encrypted_platform_tokens: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    connected_platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user", lazy="select")


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    PUBLISHED = "published"
    PARTIAL = "partial"
    FAILED = "failed"


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_duration_s: Mapped[float | None] = mapped_column(nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_platforms: Mapped[list] = mapped_column(JSON, default=list)
    platform_status: Mapped[dict] = mapped_column(JSON, default=dict)
    platform_content: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_platforms: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus, native_enum=False), default=PostStatus.DRAFT, nullable=False, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="posts")


class ContentCategory(str, enum.Enum):
    MODEL_RELEASE   = "model_release"
    RESEARCH_PAPER  = "research_paper"
    PRODUCT_LAUNCH  = "product_launch"
    FUNDING         = "funding"
    OPINION_TAKE    = "opinion_take"
    TUTORIAL        = "tutorial"
    INDUSTRY_NEWS   = "industry_news"
    OPEN_SOURCE     = "open_source"
    POLICY_SAFETY   = "policy_safety"
    OTHER           = "other"


class ContentItem(Base):
    __tablename__ = "content_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    category: Mapped[ContentCategory] = mapped_column(Enum(ContentCategory, native_enum=False), default=ContentCategory.OTHER, nullable=False, index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), index=True)
    generated_posts: Mapped[list["GeneratedPost"]] = relationship("GeneratedPost", back_populates="content_item", lazy="select")
    __table_args__ = (Index("ix_content_items_relevance", "relevance_score", "fetched_at"),)


class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_tweets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    engagement_tips: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    content_item: Mapped["ContentItem"] = relationship("ContentItem", back_populates="generated_posts")