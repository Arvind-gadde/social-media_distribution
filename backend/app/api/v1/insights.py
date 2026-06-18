"""Insights API — Agent insights and push notification registration."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import User
from app.domains.intelligence.models import WorkspaceInsight, InsightType
from app.schemas.insights import (
    WorkspaceInsightResponse,
    PushTokenRequest,
    PushTokenResponse,
)
from app.services.notifications.push_service import register_device_token
import structlog

from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=list[WorkspaceInsightResponse])
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    insight_type: Annotated[InsightType | None, Query()] = None,
    is_read: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[WorkspaceInsightResponse]:
    """Get workspace insights (agent alerts, trends, recommendations).
    
    This drives the mobile app's Home screen alert feed.
    """
    query = select(WorkspaceInsight).where(
        WorkspaceInsight.workspace_id == current_user.workspace_id,
        WorkspaceInsight.is_dismissed == False,
    )
    
    if insight_type:
        query = query.where(WorkspaceInsight.insight_type == insight_type)
    
    if is_read is not None:
        query = query.where(WorkspaceInsight.is_read == is_read)
    
    query = query.order_by(
        WorkspaceInsight.priority.desc(),
        WorkspaceInsight.created_at.desc(),
    ).limit(limit)
    
    result = await db.execute(query)
    insights = result.scalars().all()
    
    return [WorkspaceInsightResponse.model_validate(i) for i in insights]


@router.patch("/{insight_id}/read")
async def mark_insight_read(
    insight_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Mark an insight as read."""
    result = await db.execute(
        select(WorkspaceInsight).where(
            WorkspaceInsight.id == insight_id,
            WorkspaceInsight.workspace_id == current_user.workspace_id,
        )
    )
    insight = result.scalar_one_or_none()
    
    if not insight:
        return {"status": "not_found"}
    
    insight.is_read = True
    await db.commit()
    
    logger.info(
        "insight_marked_read",
        insight_id=str(insight_id),
        workspace_id=str(current_user.workspace_id),
    )
    
    return {"status": "success"}


@router.post("/notifications/register-token", response_model=PushTokenResponse)
async def register_push_token(
    request: PushTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PushTokenResponse:
    """Register Expo push token for mobile notifications.
    
    iOS/Android app sends its Expo Push Token upon login.
    """
    result = await register_device_token(
        db,
        current_user.id,
        current_user.workspace_id,
        request.token,
        request.platform,
        request.device_name,
    )
    
    return PushTokenResponse(**result)
