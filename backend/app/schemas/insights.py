"""Pydantic schemas for insights API."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.intelligence.models import InsightType


class WorkspaceInsightResponse(BaseModel):
    """Workspace insight response."""
    id: UUID
    workspace_id: UUID
    agent_type: str
    insight_type: InsightType
    title: str
    body: str
    action_type: str | None = None
    action_data: dict | None = None
    priority: int
    is_read: bool
    is_dismissed: bool
    is_actioned: bool
    expires_at: datetime | None = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class PushTokenRequest(BaseModel):
    """Request to register Expo push token."""
    token: str = Field(..., description="Expo push token")
    platform: str | None = Field(None, description="ios or android")
    device_name: str | None = Field(None, description="Device name")


class PushTokenResponse(BaseModel):
    """Response after registering push token."""
    registered: bool
    token: str
