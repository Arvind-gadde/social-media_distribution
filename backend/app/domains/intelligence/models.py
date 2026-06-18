"""Intelligence Plane Models — Content Ingestion, Enrichment, Insights, Trends.

This plane handles the "brain" of the platform:
  - Global corpus: shared source documents collected from external feeds.
  - Workspace insights: niche-specific recommendations derived for each workspace.
  - Trends: platform and niche-specific trend tracking.
  - Competitors: tracking and analysis of competitor accounts.
  - Source registry: configurable data sources per niche.

Separation rule:
  - SourceDocument / SourceRegistry are GLOBAL (shared across workspaces).
  - WorkspaceInsight / CompetitorProfile / CompetitorObservation are WORKSPACE-SCOPED.
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
# SOURCE REGISTRY — Configurable data sources per niche (GLOBAL)
# ═══════════════════════════════════════════════════════════════════════════════


class SourceType(str, enum.Enum):
    RSS = "rss"
    YOUTUBE_CHANNEL = "youtube_channel"
    SUBREDDIT = "subreddit"
    TWITTER_LIST = "twitter_list"
    API = "api"
    GITHUB_TRENDING = "github_trending"
    PRODUCT_HUNT = "product_hunt"
    ARXIV = "arxiv"
    WEB_SCRAPE = "web_scrape"


class SourceRegistry(Base):
    """Registered external feeds, APIs, channels, and crawlers.

    Niche-specific. When a workspace selects a niche, these sources
    become active for their intelligence pipeline.
    """
    __tablename__ = "source_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True, index=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False), nullable=False,
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reliability_score: Mapped[float] = mapped_column(
        Float, default=0.8, nullable=False,
    )
    scrape_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetch_frequency_minutes: Mapped[int] = mapped_column(
        Integer, default=240, nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    articles_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE DOCUMENTS — Global corpus (evolves from ContentItem)
# ═══════════════════════════════════════════════════════════════════════════════


class ContentCategory(str, enum.Enum):
    MODEL_RELEASE = "model_release"
    RESEARCH_PAPER = "research_paper"
    PRODUCT_LAUNCH = "product_launch"
    FUNDING = "funding"
    OPINION_TAKE = "opinion_take"
    TUTORIAL = "tutorial"
    INDUSTRY_NEWS = "industry_news"
    OPEN_SOURCE = "open_source"
    POLICY_SAFETY = "policy_safety"
    TREND = "trend"
    VIRAL_CONTENT = "viral_content"
    NEWS = "news"
    OTHER = "other"


class SourceDocument(Base):
    """Normalized ingested records from external sources.

    GLOBAL — shared across workspaces. This replaces the old ContentItem.
    Deduplication happens before expensive enrichment.
    """
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    source_registry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_registry.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    source_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, unique=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # AI-enriched fields
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    category: Mapped[ContentCategory] = mapped_column(
        Enum(ContentCategory, native_enum=False), default=ContentCategory.OTHER,
        nullable=False, index=True,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
    )
    tags: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)

    # Processing state
    is_processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True,
    )
    is_trending: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # Dedup cluster
    dedup_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
    )

    # Niche relevance (which niches this document is relevant to)
    niche_ids: Mapped[list | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    # Relationships
    insights: Mapped[list["SourceDocumentInsight"]] = relationship(
        "SourceDocumentInsight", back_populates="source_document", lazy="select",
    )

    __table_args__ = (
        Index("ix_source_docs_relevance", "relevance_score", "fetched_at"),
    )


class SourceDocumentInsight(Base):
    """Per-document intelligence produced by analyst and fact-checker agents.

    GLOBAL — one row per SourceDocument, upserted on each pipeline run.
    Replaces the old ContentInsight.
    """
    __tablename__ = "source_document_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # Virality signals
    virality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cross_source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trend_velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sentiment_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Value gap signals
    is_value_gap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gap_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_angle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # B-Roll / asset suggestions
    broll_assets: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Fact-check results
    fact_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fact_check_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    source_document: Mapped["SourceDocument"] = relationship(
        "SourceDocument", back_populates="insights",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE INSIGHTS — Tenant-specific recommendations (WORKSPACE-SCOPED)
# ═══════════════════════════════════════════════════════════════════════════════


class InsightType(str, enum.Enum):
    TREND_ALERT = "trend_alert"
    COMPETITOR_MOVE = "competitor_move"
    CONTENT_IDEA = "content_idea"
    GOAL_WARNING = "goal_warning"
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"
    GROWTH_HACK = "growth_hack"
    POSTING_REMINDER = "posting_reminder"
    ALGORITHM_CHANGE = "algorithm_change"
    NEWS_OPPORTUNITY = "news_opportunity"
    PERFORMANCE_INSIGHT = "performance_insight"


class WorkspaceInsight(Base):
    """Workspace-specific recommendations derived from global corpus.

    This is where shared intelligence becomes workspace value.
    Examples: "This trend is relevant to your niche",
    "Competitor X is overperforming with hooks about topic Y".
    """
    __tablename__ = "workspace_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    insight_type: Mapped[InsightType] = mapped_column(
        Enum(InsightType, native_enum=False), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    niche_relevance_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_workspace_insights_unread",
            "workspace_id", "priority",
            postgresql_where="is_read = false",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRENDS — Platform + niche-specific trend tracking (GLOBAL)
# ═══════════════════════════════════════════════════════════════════════════════


class TrendStatus(str, enum.Enum):
    RISING = "rising"
    PEAK = "peak"
    DECLINING = "declining"
    DEAD = "dead"
    EVERGREEN = "evergreen"


class TrendType(str, enum.Enum):
    HASHTAG = "hashtag"
    SOUND = "sound"
    FORMAT = "format"
    TOPIC = "topic"
    CHALLENGE = "challenge"
    MEME = "meme"


class Trend(Base):
    """Global trend tracking across platforms and niches."""
    __tablename__ = "trends"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True, index=True,
    )
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    trend_type: Mapped[TrendType] = mapped_column(
        Enum(TrendType, native_enum=False), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    example_urls: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trend_velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    peak_predicted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    peaked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[TrendStatus] = mapped_column(
        Enum(TrendStatus, native_enum=False), default=TrendStatus.RISING,
        nullable=False,
    )
    region: Mapped[str] = mapped_column(String(50), default="global", nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_trends_niche_score",
            "niche_id", "trend_score",
            postgresql_where="status IN ('rising', 'peak')",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR TRACKING (WORKSPACE-SCOPED)
# ═══════════════════════════════════════════════════════════════════════════════


class CompetitorProfile(Base):
    """External accounts or brands a workspace tracks."""
    __tablename__ = "competitor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    platform_username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True,
    )
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_engagement_rate: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
    )
    posting_frequency: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tracking_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    last_tracked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "platform", "platform_username",
            name="uq_competitor_profile",
        ),
    )

    observations: Mapped[list["CompetitorObservation"]] = relationship(
        "CompetitorObservation", back_populates="competitor", lazy="select",
    )


class CompetitorObservation(Base):
    """Timestamped observations about competitor activity."""
    __tablename__ = "competitor_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitor_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    observation_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # "post", "metric_snapshot", "format_change"
    platform_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    engagement_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    viral_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_gaps: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    competitor: Mapped["CompetitorProfile"] = relationship(
        "CompetitorProfile", back_populates="observations",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM — Workspace-aware execution tracking
# ═══════════════════════════════════════════════════════════════════════════════


class AgentRunStatus(str, enum.Enum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCESS = "success"
    PARTIAL = "partial"
    RETRYABLE_FAILED = "retryable_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class AgentRun(Base):
    """One execution of an agent or pipeline. Workspace-aware.

    Replaces the old global AgentRun.
    """
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system",
    )
    trigger: Mapped[str] = mapped_column(
        String(50), nullable=False, default="schedule",
    )
    correlation_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    run_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # "full_pipeline", "trend_scan", "competitor_check", etc.
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, native_enum=False), default=AgentRunStatus.QUEUED,
        nullable=False,
    )

    # Per-stage timing
    scout_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    analyst_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    checker_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    creative_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Counts
    items_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_fact_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gap_signals_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Error detail
    stage_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Input/output references
    input_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_agent_runs_workspace_status", "workspace_id", "status", "started_at"),
    )

    steps: Mapped[list["AgentStep"]] = relationship(
        "AgentStep", back_populates="agent_run", lazy="select",
    )


class AgentStep(Base):
    """Individual step within an agent run.

    Captures tool/provider usage, latency, token usage, and results.
    """
    __tablename__ = "agent_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    agent_run: Mapped["AgentRun"] = relationship(
        "AgentRun", back_populates="steps",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT CATALOG & VERSIONING — Traceable AI artifact generation
# ═══════════════════════════════════════════════════════════════════════════════


class PromptCatalog(Base):
    """Named prompt templates for AI generation.

    Every generated business artifact should be traceable to:
      - prompt name + version
      - provider + model family
      - sampling policy + tool set
    """
    __tablename__ = "prompt_catalog"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )  # "content.score", "content.critique", "trend.analyze"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # "scorer", "analyst", "creative", "fact_checker"
    # Niche-specific override support
    niche_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("niches.id"), nullable=True,
    )
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion", back_populates="catalog", lazy="select",
    )


class PromptVersion(Base):
    """Immutable prompt snapshots with rollout metadata.

    Never edit in place — always create a new version with a new SHA.
    """
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_catalog.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # "v1.0", "v1.1", etc.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Model suggestions
    recommended_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recommended_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    # Rollout metadata
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rollout_pct: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("catalog_id", "version", name="uq_prompt_version"),
    )

    catalog: Mapped["PromptCatalog"] = relationship(
        "PromptCatalog", back_populates="versions",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER POLICY — Model routing rules by task type
# ═══════════════════════════════════════════════════════════════════════════════


class ProviderPolicy(Base):
    """Routing rules for model/provider selection by task type.

    Centralized provider routing in policy, not scattered service code.
    Routing policy from openai.md §8.7:
      - Ingestion/large-context triage → Gemini primary
      - Structured generation/tool use → OpenAI primary
      - Critique/refinement/review → Anthropic primary
    """
    __tablename__ = "provider_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
    )  # "scoring", "generation", "critique", "analysis", "ingestion"
    primary_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_model: Mapped[str] = mapped_column(String(100), nullable=False)
    fallback_provider_1: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_model_1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_provider_2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_model_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("task_type", name="uq_provider_policy_task"),
    )



# ═══════════════════════════════════════════════════════════════════════════════
# AGENT CONFIGURATION — Per-workspace agent settings
# ═══════════════════════════════════════════════════════════════════════════════


class AgentConfig(Base):
    """Per-workspace agent configuration and scheduling.
    
    Each workspace can enable/disable agents and configure their behavior.
    """
    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'niche_intelligence','trend_detection','analytics','competitor',
    # 'content_ideation','goal_accountability','collaboration_business',
    # 'news_research','tips_tricks','smart_scheduling','growth_optimization',
    # 'video_intelligence','predictive_virality','orchestrator'
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    run_frequency: Mapped[str] = mapped_column(
        String(20), default="hourly", nullable=False,
    )
    # hourly|every_6h|daily|weekly|on_demand|real_time
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    # Agent-specific config: {"niches": ["tech"], "keywords": [...], "depth": "deep"}
    llm_model: Mapped[str] = mapped_column(
        String(50), default="gpt-4o", nullable=False,
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_type", name="uq_agent_config"),
    )


class AgentInsight(Base):
    """Agent-generated insights and recommendations for a workspace.
    
    This is the primary output of the agent system - actionable insights
    that appear in the user's feed.
    """
    __tablename__ = "agent_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    insight_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 'trend_alert','competitor_move','content_idea','goal_warning',
    # 'collaboration_opportunity','growth_hack','posting_reminder','contract_opportunity'
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # 1-10, 10 = highest
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_agent_insights_unread",
            "workspace_id", "priority",
            postgresql_where="is_read = false AND is_dismissed = false",
        ),
    )
