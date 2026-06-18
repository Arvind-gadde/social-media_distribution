"""Control Plane Models — Identity, Workspaces, Roles, Niches, Audit, Metering.

These models form the tenant boundary and governance layer of the platform.
Every creator-owned record in the system references a workspace_id from here.

Design rules:
  - UUID primary keys everywhere (no sequential IDs exposed).
  - Soft deletes with `deleted_at` timestamps.
  - Audit columns: `created_at`, `updated_at`.
  - JSONB for flexible metadata, NOT for critical workflow state.
  - Append-only for audit_logs and usage_meters.
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
# WORKSPACES — Primary tenant boundary
# ═══════════════════════════════════════════════════════════════════════════════


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class Workspace(Base):
    """Primary tenant boundary.

    One solo creator gets one default workspace.
    Agencies can own many workspaces.
    All creator-owned records reference workspace_id.
    """
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, native_enum=False), default=PlanTier.FREE, nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
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

    # ═══════════════════════════════════════════════════════════════════════
    # STRIPE BILLING (Phase 11)
    # ═══════════════════════════════════════════════════════════════════════
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(200), unique=True, nullable=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(200), unique=True, nullable=True,
    )
    subscription_tier: Mapped[str] = mapped_column(
        String(20), default="free", nullable=False,
    )  # free, pro, business, enterprise
    subscription_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False,
    )  # active, past_due, canceled, trialing
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # Relationships
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="workspace", lazy="select",
    )
    niches: Mapped[list["WorkspaceNiche"]] = relationship(
        "WorkspaceNiche", back_populates="workspace", lazy="select",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE MEMBERSHIPS — Maps users to workspaces with roles
# ═══════════════════════════════════════════════════════════════════════════════


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    ANALYST = "analyst"
    VIEWER = "viewer"


class InviteStatus(str, enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class WorkspaceMembership(Base):
    """Maps users to workspaces with a role and status."""
    __tablename__ = "workspace_memberships"

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
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, native_enum=False), default=WorkspaceRole.OWNER,
        nullable=False,
    )
    invite_status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, native_enum=False), default=InviteStatus.ACTIVE,
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="memberships",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NICHES — Core personalization system
# ═══════════════════════════════════════════════════════════════════════════════


class Niche(Base):
    """Seeded niche definitions — not user-created.

    The entire app adapts to these categories. Every agent prompt,
    every data source, every content suggestion is niche-contextualized.
    """
    __tablename__ = "niches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    parent_niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True,
    )
    keywords: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    hashtags: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    content_types: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    platforms: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    source_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    children: Mapped[list["Niche"]] = relationship(
        "Niche", back_populates="parent", lazy="select",
    )
    parent: Mapped["Niche | None"] = relationship(
        "Niche", back_populates="children", remote_side=[id], lazy="select",
    )


class WorkspaceNiche(Base):
    """User's niche selections with personalization.

    A workspace can have multiple niches with a primary flag.
    Content pillars and target audience are workspace-specific.
    """
    __tablename__ = "workspace_niches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    niche_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=False, index=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_pillars: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    target_audience: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "niche_id", name="uq_workspace_niche"),
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="niches",
    )
    niche: Mapped["Niche"] = relationship("Niche", lazy="select")


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL ACCOUNTS — Explicit model (replaces JSON blob on User)
# ═══════════════════════════════════════════════════════════════════════════════


class TokenStatus(str, enum.Enum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REFRESH_FAILED = "refresh_failed"


class SocialAccount(Base):
    """Connected external platform account.

    Tokens are encrypted at rest. Never exposed to frontend.
    """
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(200), nullable=False)
    platform_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_display_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    platform_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    token_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, native_enum=False), default=TokenStatus.VALID,
        nullable=False,
    )
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    permissions: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    rate_limit_state: Mapped[dict | None] = mapped_column(
        JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "platform", "platform_user_id",
            name="uq_social_account",
        ),
        Index("ix_social_accounts_workspace_active", "workspace_id", "is_active"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG — Append-only, never mutated
# ═══════════════════════════════════════════════════════════════════════════════


class AuditLog(Base):
    """Append-only audit trail for sensitive actions.

    Every high-impact action needs a clear source, actor, context,
    and decision trail. This is a core governance primitive.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # UUID or "system"
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_workspace_actor", "workspace_id", "actor_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE METER — Append-only cost accounting
# ═══════════════════════════════════════════════════════════════════════════════


class UsageMeter(Base):
    """Append-only usage and cost accounting events.

    Tracks: LLM tokens, transcription minutes, image generations,
    video processing minutes, publish attempts, storage growth.
    """
    __tablename__ = "usage_meters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    meter_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # "llm_tokens_in", "llm_tokens_out", "publish_attempt", etc.
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    billable_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_usage_workspace_type", "workspace_id", "meter_type", "recorded_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET POLICY — Workspace spending limits & throttles
# ═══════════════════════════════════════════════════════════════════════════════


class BudgetPolicy(Base):
    """Defines workspace budgets, throttles, and approval thresholds.

    Controls:
      - auto-downgrade to cheaper model for low-priority analysis
      - stop after N failed provider attempts
      - require approval before expensive media generation
    """
    __tablename__ = "budget_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Monthly spending limits
    monthly_llm_budget_usd: Mapped[float] = mapped_column(
        Float, default=10.0, nullable=False,
    )
    monthly_media_budget_usd: Mapped[float] = mapped_column(
        Float, default=5.0, nullable=False,
    )
    # Per-run limits
    max_cost_per_run_usd: Mapped[float] = mapped_column(
        Float, default=0.50, nullable=False,
    )
    # Throttles
    max_publish_per_day: Mapped[int] = mapped_column(
        Integer, default=20, nullable=False,
    )
    max_agent_runs_per_day: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False,
    )
    # Approval thresholds
    approval_required_above_usd: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False,
    )
    # Automatic model downgrade when budget > X%
    auto_downgrade_threshold_pct: Mapped[int] = mapped_column(
        Integer, default=80, nullable=False,
    )
    # Whether to hard-stop or soft-warn on budget exhaustion
    hard_stop_on_budget: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OUTBOX EVENT — Durable downstream event delivery
# ═══════════════════════════════════════════════════════════════════════════════


class OutboxStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxEvent(Base):
    """Durable events for asynchronous downstream work.

    Use cases:
      - send notification
      - trigger operator alert
      - sync analytics rollup
      - export billing event
      - invoke external integration

    Never rely on "write DB row and hope another service noticed".
    """
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # "notification.send", "analytics.sync", "billing.export"
    aggregate_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # "publish_job", "agent_run", "content_variant"
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, native_enum=False), default=OutboxStatus.PENDING,
        nullable=False,
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_outbox_pending", "status", "next_attempt_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK RECEIPT — Inbound platform event tracking
# ═══════════════════════════════════════════════════════════════════════════════


class WebhookProcessingStatus(str, enum.Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    DUPLICATE = "duplicate"
    PROCESSED = "processed"
    RETRYABLE_FAILED = "retryable_failed"
    FAILED = "failed"


class WebhookReceipt(Base):
    """Stores raw inbound platform events with dedupe, validation, and processing status.

    Flow: received → validated → processed
    Dedupe: (provider, external_event_id) or (provider, payload_hash)
    """
    __tablename__ = "webhook_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_status: Mapped[WebhookProcessingStatus] = mapped_column(
        Enum(WebhookProcessingStatus, native_enum=False),
        default=WebhookProcessingStatus.RECEIVED, nullable=False,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    linked_resource_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    linked_resource_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_webhook_provider_event", "provider", "external_event_id"),
        Index("ix_webhook_provider_hash", "provider", "payload_hash"),
    )

