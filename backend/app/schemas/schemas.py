"""Pydantic schemas — request/response contracts."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    connected_platforms: list[str]
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class AuthResponse(BaseModel):
    user: UserResponse

class PostCreateRequest(BaseModel):
    caption: str = Field(default="", max_length=5000)
    target_platforms: list[str] = Field(min_length=1)
    title: Optional[str] = Field(default=None, max_length=500)
    scheduled_at: Optional[datetime] = None

    @field_validator("target_platforms")
    @classmethod
    def validate_platforms(cls, v: list[str]) -> list[str]:
        from app.constants import PLATFORM_CHAR_LIMITS
        invalid = [p for p in v if p not in PLATFORM_CHAR_LIMITS]
        if invalid:
            raise ValueError(f"Unknown platforms: {invalid}")
        return v

class PostResponse(BaseModel):
    id: UUID
    title: Optional[str]
    caption: Optional[str]
    media_url: Optional[str]
    media_type: Optional[str]
    target_platforms: list[str]
    platform_status: dict[str, Any]
    platform_content: dict[str, Any]
    recommended_platforms: list[str]
    status: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}

class PlatformRecommendation(BaseModel):
    platform: str
    reason: str
    score: float

class AICaptionRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    tone: str = "casual"
    language: str = "en"
    media_type: str = "video"
    platforms: list[str] = []

class AICaptionResponse(BaseModel):
    caption: str

class HashtagResponse(BaseModel):
    hashtags: list[str]

class AnalyticsSummary(BaseModel):
    total_posts: int
    published_posts: int
    partial_posts: int
    failed_posts: int
    platform_distribution: dict[str, int]
    platform_success_rate: dict[str, float]

class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict[str, str]
