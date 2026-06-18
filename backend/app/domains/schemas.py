"""Pydantic schemas for API request/response validation.

Organized by domain plane. All workspace-scoped resources include workspace_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROL PLANE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
    timezone: str = Field(default="UTC", max_length=50)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        return v.lower()


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: Optional[str] = None
    plan_tier: str
    timezone: str
    onboarding_completed: bool
    onboarding_step: int
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    timezone: Optional[str] = None
    avatar_url: Optional[str] = None


class NicheResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    keywords: Optional[list[str]] = None
    hashtags: Optional[list[str]] = None
    content_types: Optional[list[str]] = None
    platforms: Optional[list[str]] = None
    parent_niche_id: Optional[uuid.UUID] = None
    children: Optional[list["NicheResponse"]] = None

    model_config = {"from_attributes": True}


class WorkspaceNicheSelect(BaseModel):
    niche_id: uuid.UUID
    is_primary: bool = False
    content_pillars: Optional[list[str]] = None
    target_audience: Optional[dict] = None


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: Optional[str] = None
    platform_display_name: Optional[str] = None
    platform_avatar_url: Optional[str] = None
    followers_count: int = 0
    engagement_rate: float = 0.0
    is_active: bool = True
    is_primary: bool = False
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# ONBOARDING SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class OnboardingStepNiches(BaseModel):
    """Step 2: Select niches."""
    niches: list[WorkspaceNicheSelect] = Field(..., min_length=1, max_length=5)


class OnboardingStepGoals(BaseModel):
    """Step 4: Set initial goals."""
    weekly_posts_target: int = Field(default=3, ge=1, le=30)
    follower_target_monthly: Optional[int] = None
    primary_platform: Optional[str] = None


class OnboardingComplete(BaseModel):
    """Mark onboarding as done."""
    completed: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE PLANE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class WorkspaceInsightResponse(BaseModel):
    id: uuid.UUID
    insight_type: str
    agent_type: str
    title: str
    body: str
    action_type: Optional[str] = None
    action_data: Optional[dict] = None
    niche_relevance_score: float = 0.0
    priority: int = 5
    is_read: bool = False
    is_actioned: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendResponse(BaseModel):
    id: uuid.UUID
    niche_id: Optional[uuid.UUID] = None
    platform: Optional[str] = None
    trend_type: str
    title: str
    description: Optional[str] = None
    hashtags: Optional[list[str]] = None
    trend_score: float = 0.0
    trend_velocity: float = 0.0
    status: str
    region: str = "global"
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetitorCreate(BaseModel):
    platform: str = Field(..., max_length=30)
    platform_username: str = Field(..., max_length=100)
    niche_id: Optional[uuid.UUID] = None


class CompetitorResponse(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    followers_count: int = 0
    avg_engagement_rate: float = 0.0
    posting_frequency: float = 0.0
    is_active: bool = True
    last_tracked_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION PLANE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class ContentProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    content_type: Optional[str] = None
    niche_id: Optional[uuid.UUID] = None
    content_pillars: Optional[list[str]] = None
    mood: Optional[str] = None
    target_platforms: Optional[list[str]] = None
    source_insight_id: Optional[uuid.UUID] = None
    source_trend_id: Optional[uuid.UUID] = None


class ContentProjectResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    content_type: Optional[str] = None
    status: str
    target_platforms: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    virality_score: Optional[float] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentVariantResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    target_platform: str
    hook: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    call_to_action: Optional[str] = None
    script_outline: Optional[str] = None
    thread_tweets: Optional[list] = None
    engagement_tips: Optional[list] = None
    authoring_source: str
    approval_state: str
    total_views: int = 0
    total_likes: int = 0
    engagement_rate: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    goal_type: str
    period: str
    target_value: float = Field(..., gt=0)
    unit: str
    platform: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    reminder_enabled: bool = True
    reminder_schedule: Optional[dict] = None


class GoalResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    goal_type: str
    period: str
    target_value: float
    current_value: float
    unit: str
    platform: Optional[str] = None
    status: str
    starts_at: datetime
    ends_at: datetime
    streak_count: int = 0
    best_streak: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def progress_pct(self) -> float:
        if self.target_value <= 0:
            return 0.0
        return min(round((self.current_value / self.target_value) * 100, 1), 100.0)


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_value: Optional[float] = None
    status: Optional[str] = None
    reminder_enabled: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    run_type: str
    status: str
    trigger: str
    correlation_id: str
    items_fetched: int = 0
    items_new: int = 0
    items_scored: int = 0
    items_generated: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    stage_errors: Optional[list] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentTriggerRequest(BaseModel):
    run_type: str = "full_pipeline"
    skip_creative: bool = False
