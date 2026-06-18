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
    connected_platforms: list[str] = []
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse


# ── Email / Password Auth ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    timezone: Optional[str] = Field(default="UTC")
    locale: Optional[str] = Field(default="en")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Require strong password:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not has_upper:
            raise ValueError("Password must contain at least one uppercase letter")
        if not has_lower:
            raise ValueError("Password must contain at least one lowercase letter")
        if not has_digit:
            raise ValueError("Password must contain at least one digit")
        if not has_special:
            raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
        
        return v

    @field_validator("name")
    @classmethod
    def name_no_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()
    
    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            return None
        # Username must be alphanumeric with underscores/hyphens
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        if v[0] in "_-" or v[-1] in "_-":
            raise ValueError("Username cannot start or end with underscore or hyphen")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ── Posts ─────────────────────────────────────────────────────────────────

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