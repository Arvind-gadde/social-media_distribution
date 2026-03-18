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

# ─────────────────────────────────────────────────────────────────────────────
# Orchestration layer — added by multi-agent pipeline
# ─────────────────────────────────────────────────────────────────────────────

class AgentStatus(str, enum.Enum):
    RUNNING  = "running"
    SUCCESS  = "success"
    PARTIAL  = "partial"   # some agents failed, pipeline continued
    FAILED   = "failed"


class AgentRun(Base):
    """One execution of the full orchestrator pipeline.

    Inserted when the orchestrator starts; updated when it finishes.
    Partial failures are expected (e.g. fact-checker times out) and stored
    as PARTIAL so the dashboard can show pipeline health over time.
    """
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    triggered_by: Mapped[str] = mapped_column(
        String(50), nullable=False, default="celery_beat"
    )  # "celery_beat" | "manual_api" | "test"

    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, native_enum=False), default=AgentStatus.RUNNING, nullable=False
    )

    # Per-stage timing in seconds (null = stage did not run)
    scout_duration_s:    Mapped[float | None] = mapped_column(nullable=True)
    analyst_duration_s:  Mapped[float | None] = mapped_column(nullable=True)
    checker_duration_s:  Mapped[float | None] = mapped_column(nullable=True)
    creative_duration_s: Mapped[float | None] = mapped_column(nullable=True)

    # Counts
    items_fetched:    Mapped[int] = mapped_column(default=0, nullable=False)
    items_new:        Mapped[int] = mapped_column(default=0, nullable=False)
    items_scored:     Mapped[int] = mapped_column(default=0, nullable=False)
    items_fact_checked: Mapped[int] = mapped_column(default=0, nullable=False)
    items_generated:  Mapped[int] = mapped_column(default=0, nullable=False)
    gap_signals_found: Mapped[int] = mapped_column(default=0, nullable=False)

    # Error detail per failed stage (JSON: {"stage": "analyst", "error": "..."})
    stage_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    started_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_agent_runs_started", "started_at"),)


class ContentInsight(Base):
    """Per-item intelligence produced by the analyst and fact-checker agents.

    One row per ContentItem, upserted on each pipeline run so re-runs
    refresh stale data rather than accumulating duplicates.
    """
    __tablename__ = "content_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one insight row per item
        index=True,
    )

    # ── Virality signals ──────────────────────────────────────────────────
    virality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cross_source_count: Mapped[int] = mapped_column(default=1, nullable=False)
    trend_velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Serialised as {"positive": 0.6, "negative": 0.1, "controversial": 0.3}
    sentiment_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Value Gap signals ─────────────────────────────────────────────────
    # True when analyst decided this item covers an underexplored angle
    is_value_gap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gap_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Suggested unique angle to take when making content
    suggested_angle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── B-Roll / asset suggestions ────────────────────────────────────────
    # [{"type": "github", "url": "...", "label": "..."}, ...]
    broll_assets: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Fact-check results ────────────────────────────────────────────────
    fact_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fact_check_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # [{"claim": "...", "verdict": "verified|unverified|disputed", "note": "..."}]
    flagged_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    content_item: Mapped["ContentItem"] = relationship("ContentItem")
