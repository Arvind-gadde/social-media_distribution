"""Analytics routes."""
from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/analytics", tags=["analytics"])


# TODO: Implement analytics with proper models
# This endpoint needs to be reimplemented with the correct repository and models
# @router.get("/summary", response_model=AnalyticsSummary)
# async def get_summary(current_user: CurrentUser, db: DbSession) -> AnalyticsSummary:
#     pass
