"""Business Domain Models — DM Inbox, Collaborations, Contracts.

Handles the creator business pipeline:
  - DM ingestion and AI classification
  - Deal pipeline tracking
  - Contract generation and management
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# DM INBOX — Inbound message tracking and AI classification
# ═══════════════════════════════════════════════════════════════════════════════


class DMCategory(str, enum.Enum):
    """AI-classified DM categories."""
    BRAND_DEAL = "brand_deal"
    COLLAB = "collab"
    FAN = "fan"
    SPAM = "spam"
    HATE = "hate"
    QUESTION = "question"
    SUPPORT = "support"
    UNKNOWN = "unknown"


class DMInbox(Base):
    """Inbound DM tracking with AI classification.
    
    Flow:
      1. Celery task fetches DMs from platform APIs
      2. Stores raw message
      3. AI evaluator classifies and extracts business info
      4. If brand_deal, creates Collaboration record
    """
    __tablename__ = "dm_inbox"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    
    # Platform details
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    platform_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sender_platform_id: Mapped[str] = mapped_column(String(200), nullable=False)
    sender_username: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sender_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_followers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Message content
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # AI Analysis
    is_business_inquiry: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    ai_category: Mapped[DMCategory | None] = mapped_column(
        Enum(DMCategory, native_enum=False), nullable=True,
    )
    ai_priority: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False,
    )  # 1-10, 10 = highest
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_sentiment: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True,
    )  # -1.0 to 1.0
    ai_suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    
    # Link to collaboration if created
    collaboration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collaborations.id", use_alter=True, name="fk_dm_inbox_collaboration_id"),
        nullable=True,
    )
    
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_dm_workspace_unread", "workspace_id", "is_read", "ai_priority"),
        Index("ix_dm_platform_message", "platform", "platform_message_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COLLABORATION — Deal pipeline tracking
# ═══════════════════════════════════════════════════════════════════════════════


class CollaborationType(str, enum.Enum):
    """Type of collaboration deal."""
    BRAND_DEAL = "brand_deal"
    SPONSORSHIP = "sponsorship"
    AFFILIATE = "affiliate"
    UGC = "ugc"
    COLLAB = "collab"
    PR = "pr"
    OTHER = "other"


class CollaborationStatus(str, enum.Enum):
    """Deal pipeline stages."""
    INQUIRY = "inquiry"
    NEGOTIATING = "negotiating"
    CONTRACT_SENT = "contract_sent"
    CONTRACT_SIGNED = "contract_signed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PaymentType(str, enum.Enum):
    """Payment structure."""
    FLAT_FEE = "flat_fee"
    CPM = "cpm"
    REVENUE_SHARE = "revenue_share"
    BARTER = "barter"
    HYBRID = "hybrid"


class PaymentStatus(str, enum.Enum):
    """Payment tracking."""
    PENDING = "pending"
    INVOICED = "invoiced"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Collaboration(Base):
    """Deal pipeline tracking with AI scoring.
    
    Tracks brand deals from inquiry to completion.
    AI scores deal quality and provides negotiation advice.
    """
    __tablename__ = "collaborations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    
    # Deal type and status
    collab_type: Mapped[CollaborationType] = mapped_column(
        Enum(CollaborationType, native_enum=False),
        default=CollaborationType.BRAND_DEAL, nullable=False,
    )
    status: Mapped[CollaborationStatus] = mapped_column(
        Enum(CollaborationStatus, native_enum=False),
        default=CollaborationStatus.INQUIRY, nullable=False,
    )
    
    # Brand details
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Deal details
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables: Mapped[list | None] = mapped_column(
        JSON, default=list, nullable=True,
    )  # [{"type": "reel", "count": 2, "platform": "instagram"}]
    
    # Financials
    offered_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )
    negotiated_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )
    final_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_type: Mapped[PaymentType | None] = mapped_column(
        Enum(PaymentType, native_enum=False), nullable=True,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING, nullable=False,
    )
    
    # AI analysis
    ai_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True,
    )  # 0.0 to 1.0
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_red_flags: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    
    # Source tracking
    source: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )  # "inbound_dm", "email", "outbound"
    source_platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_dm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dm_inbox.id"), nullable=True,
    )
    
    # Timeline
    deal_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    deal_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    
    # Notes and tags
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_tags: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
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

    __table_args__ = (
        Index("ix_collab_workspace_status", "workspace_id", "status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACT DRAFT — AI-generated legal agreements
# ═══════════════════════════════════════════════════════════════════════════════


class ContractStatus(str, enum.Enum):
    """Contract lifecycle stages."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    COUNTERSIGNED = "countersigned"
    EXPIRED = "expired"
    VOIDED = "voided"


class ContractDraft(Base):
    """AI-generated contract drafts with review tracking.
    
    Generated when user moves deal to contract_sent stage.
    Includes standard FTC disclosure and payment terms.
    """
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    collaboration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collaborations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    
    # Contract details
    contract_type: Mapped[str] = mapped_column(
        String(30), default="ai_generated", nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown or HTML
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status tracking
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, native_enum=False),
        default=ContractStatus.DRAFT, nullable=False,
    )
    
    # Signature tracking
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    signature_provider: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )  # "docusign", "hellosign", "manual"
    external_contract_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    
    # AI review
    ai_review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_red_flags: Mapped[list | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_contract_collab_status", "collaboration_id", "status"),
    )
