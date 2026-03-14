"""Push notification routes."""
from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import CurrentUser, Cache
from app.schemas.schemas import PushSubscriptionRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/subscribe", status_code=201)
async def subscribe(
    req: PushSubscriptionRequest, current_user: CurrentUser, cache: Cache
) -> dict:
    await cache.save_push_subscription(
        str(current_user.id),
        {"endpoint": req.endpoint, "keys": req.keys},
    )
    return {"status": "subscribed"}


@router.delete("/unsubscribe")
async def unsubscribe(current_user: CurrentUser, cache: Cache) -> dict:
    await cache.delete(f"push_sub:{current_user.id}")
    return {"status": "unsubscribed"}
