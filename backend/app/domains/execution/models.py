"""Execution Plane Models — Content Lifecycle, Publishing, Goals, Approvals.

This plane handles the "doing" of the platform:
  - ContentProject: top-level content unit for a workspace
  - ContentVariant: platform-specific versions (replaces GeneratedPost)
  - ContentAsset: uploaded or derived media
  - PublishJob / PublishAttempt: durable publishing with retry safety
  - CreatorGoal / GoalCheckIn: accountability system
  - ApprovalRequest: gated action approvals
  - Notification: cross-channel notification delivery

All models are WORKSPACE-SCOPED.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT PROJECTS — Top-level content unit
# ═══════════════════════════════════════════════════════════════════════════════


class ProjectStatus(str, enum.Enum):
    IDEA = "idea"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"


class ContentProject(Base):
    """Top-level content unit for a workspace.

    Groups a campaign, a post package, or a cross-platform release.
    Can be created from a WorkspaceInsight, a trend, or manually.
    """
    __tablename__ = "content_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )  # 'reel','short','post','carousel','story','thread','blog'
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False), default=ProjectStatus.IDEA,
        nullable=False, index=True,
    )
    niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True,
    )
    content_pillars: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    source_insight_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace_insights.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_trend_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trends.id", ondelete="SET NULL"),
        nullable=True,
    )
    mood: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )  # 'educational','entertaining','inspirational','promotional'
    hooks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    target_platforms: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # AI analysis
    virality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    __table_args__ = (
        Index(
            "ix_content_projects_workspace_status",
            "workspace_id", "status", "created_at",
        ),
    )

    variants: Mapped[list["ContentVariant"]] = relationship(
        "ContentVariant", back_populates="project", lazy="select",
    )
    assets: Mapped[list["ContentAsset"]] = relationship(
        "ContentAsset", back_populates="project", lazy="select",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT VARIANTS — Platform-specific versions (replaces GeneratedPost)
# ═══════════════════════════════════════════════════════════════════════════════


class AuthoringSource(str, enum.Enum):
    HUMAN = "human"
    ASSISTANT = "assistant"
    HYBRID = "hybrid"


class ApprovalState(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentVariant(Base):
    """Platform-specific generated or human-authored content variant.

    Replaces the old GeneratedPost. First-class record, not a transient blob.
    Prompt version and provider metadata are attached for traceability.
    """
    __tablename__ = "content_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_platform: Mapped[str] = mapped_column(String(30), nullable=False)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_tweets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    engagement_tips: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Authoring metadata
    authoring_source: Mapped[AuthoringSource] = mapped_column(
        Enum(AuthoringSource, native_enum=False), default=AuthoringSource.ASSISTANT,
        nullable=False,
    )
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Approval
    approval_state: Mapped[ApprovalState] = mapped_column(
        Enum(ApprovalState, native_enum=False), default=ApprovalState.NOT_REQUIRED,
        nullable=False,
    )

    # Performance after publishing
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    project: Mapped["ContentProject"] = relationship(
        "ContentProject", back_populates="variants",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT ASSETS — Media objects
# ═══════════════════════════════════════════════════════════════════════════════


class ContentAsset(Base):
    """Uploaded or derived media objects."""
    __tablename__ = "content_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    media_kind: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # "video", "image", "audio", "document", "thumbnail"
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_lineage: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )  # "upload", "generated", "derived", "transcoded"
    retention_class: Mapped[str] = mapped_column(
        String(30), default="standard", nullable=False,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    project: Mapped["ContentProject | None"] = relationship(
        "ContentProject", back_populates="assets",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLISH JOBS & ATTEMPTS — Durable publishing with retry safety
# ═══════════════════════════════════════════════════════════════════════════════


class PublishStatus(str, enum.Enum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    RETRYABLE_FAILED = "retryable_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class PublishJob(Base):
    """Scheduled delivery unit — one variant to one platform at one time.

    Uses idempotency keys and lease-based concurrency control.
    """
    __tablename__ = "publish_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_platform: Mapped[str] = mapped_column(String(30), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, native_enum=False), default=PublishStatus.QUEUED,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False,
    )
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_lease_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    platform_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    platform_post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_publish_jobs_schedule",
            "workspace_id", "scheduled_at", "status",
        ),
    )

    attempts: Mapped[list["PublishAttempt"]] = relationship(
        "PublishAttempt", back_populates="publish_job", lazy="select",
    )


class PublishAttempt(Base):
    """Every real publish call to an external provider.

    IMMUTABLE — never overwrite attempt history.
    """
    __tablename__ = "publish_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    publish_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publish_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    provider_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    publish_job: Mapped["PublishJob"] = relationship(
        "PublishJob", back_populates="attempts",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CREATOR GOALS & ACCOUNTABILITY
# ═══════════════════════════════════════════════════════════════════════════════


class GoalType(str, enum.Enum):
    CONTENT_COUNT = "content_count"
    FOLLOWERS = "followers"
    VIEWS = "views"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    CUSTOM = "custom"


class GoalPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class CreatorGoal(Base):
    """Goal and accountability tracking for creators.

    Supports posting frequency goals, follower targets, engagement targets.
    The Goal Agent monitors progress and sends smart reminders.
    """
    __tablename__ = "creator_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal_type: Mapped[GoalType] = mapped_column(
        Enum(GoalType, native_enum=False), nullable=False,
    )
    period: Mapped[GoalPeriod] = mapped_column(
        Enum(GoalPeriod, native_enum=False), nullable=False,
    )
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # 'posts','followers','views','dollars','percent'
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, native_enum=False), default=GoalStatus.ACTIVE,
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )
    reminder_schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    check_ins: Mapped[list["GoalCheckIn"]] = relationship(
        "GoalCheckIn", back_populates="goal", lazy="select",
    )


class GoalCheckIn(Base):
    """Periodic check-in on goal progress."""
    __tablename__ = "goal_check_ins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creator_goals.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    value_at_checkin: Mapped[float] = mapped_column(Float, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    goal: Mapped["CreatorGoal"] = relationship(
        "CreatorGoal", back_populates="check_ins",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVAL REQUESTS — Gated action approvals
# ═══════════════════════════════════════════════════════════════════════════════


class ApprovalDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(Base):
    """Formal approval object for gated actions.

    Used for: auto-publish in team workspaces, expensive AI operations,
    sponsor-facing replies, cost escalation.
    """
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decision: Mapped[ApprovalDecision] = mapped_column(
        Enum(ApprovalDecision, native_enum=False), default=ApprovalDecision.PENDING,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
        onupdate=_utcnow,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class Notification(Base):
    """Cross-channel notifications (in-app, push, email)."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_push_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id", "scheduled_for",
            postgresql_where="is_read = false",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIA EDITS — Video processing pipeline state machine
# ═══════════════════════════════════════════════════════════════════════════════


class MediaEditStatus(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    RENDERING = "rendering"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaEdit(Base):
    """Video processing job state machine.

    Tracks the lifecycle of video editing operations from raw upload
    through AI analysis, FFmpeg rendering, and final output.

    Can be linked to a ContentItem for formal publishing workflow,
    or exist independently for quick edits.
    """
    __tablename__ = "media_edits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Storage pointers
    original_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    edited_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # State machine
    status: Mapped[MediaEditStatus] = mapped_column(
        Enum(MediaEditStatus, native_enum=False), default=MediaEditStatus.QUEUED,
        nullable=False, index=True,
    )

    # Edit configuration
    target_platform: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # instagram_reel, youtube_shorts, tiktok, etc
    aspect_ratio: Mapped[str] = mapped_column(
        String(10), default="9:16", nullable=False,
    )
    edit_recipe: Mapped[dict | None] = mapped_column(
        JSON, default=dict, nullable=True,
    )
    # Example: {"trim": {"start": 12, "end": 45}, "auto_caption": true, 
    #           "volume_boost": 1.5, "add_music": false}

    # AI analysis results
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_hook_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Example: {"start_sec": 12, "end_sec": 45, "reasoning": "..."}
    suggested_captions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Video metadata
    original_duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    edited_duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    original_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edited_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Telemetry
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    # Worker lease (for concurrency control)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_lease_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_media_edits_workspace_status",
            "workspace_id", "status", "created_at",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS FACTS — Append-only measurements from platforms
# ═══════════════════════════════════════════════════════════════════════════════


class AnalyticsFact(Base):
    """Immutable or append-preferred analytics measurements.

    Captures engagement metrics from social platforms after publishing.
    One row per content variant per platform per measurement timestamp.
    """
    __tablename__ = "analytics_facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )

    # Engagement metrics
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    link_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Video-specific
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_watch_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Revenue
    estimated_revenue_usd: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
    )

    # Engagement rate (derived)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Comment intelligence
    sentiment_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    top_comments: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Raw platform data
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_analytics_workspace_recorded",
            "workspace_id", "platform", "recorded_at",
        ),
    )

