"""Posts routes — upload, list, get, retry, delete."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, Query
from fastapi.responses import JSONResponse
from app.api.deps import CurrentUser, PostSvc, MediaSvc
from app.exceptions import ValidationError
from app.models.models import PostStatus
from app.schemas.schemas import PostResponse
from app.workers.tasks import distribute_post

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostResponse, status_code=201)
async def upload_post(
    current_user: CurrentUser,
    post_service: PostSvc,
    media_service: MediaSvc,
    caption: str = Form(default=""),
    target_platforms: str = Form(...),
    title: Optional[str] = Form(default=None),
    scheduled_at: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> PostResponse:
    import json
    try:
        platforms = json.loads(target_platforms)
    except Exception:
        raise ValidationError("target_platforms must be a JSON array")

    media_key, media_url, media_type, duration = None, None, "text", None

    if file and file.filename:
        media_key, media_url = await media_service.upload(file, str(current_user.id))
        media_type = media_service.detect_media_type(file.content_type or "")

    scheduled = None
    if scheduled_at:
        try:
            scheduled = datetime.fromisoformat(scheduled_at)
        except ValueError:
            raise ValidationError("scheduled_at must be ISO 8601 format")

    post = await post_service.create_draft(
        current_user.id,
        caption=caption,
        target_platforms=platforms,
        media_key=media_key,
        media_url=media_url,
        media_type=media_type,
        media_duration_s=duration,
        title=title,
        scheduled_at=scheduled,
    )

    if not scheduled:
        distribute_post.delay(str(post.id))
    else:
        distribute_post.apply_async(args=[str(post.id)], eta=scheduled)

    return PostResponse.model_validate(post)


@router.get("", response_model=list[PostResponse])
async def list_posts(
    current_user: CurrentUser,
    post_service: PostSvc,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PostResponse]:
    from app.repositories.repositories import PostRepository
    from app.db.session import AsyncSessionLocal
    status_enum = PostStatus(status) if status else None
    posts = await post_service._repo.list_for_user(
        current_user.id, status=status_enum, limit=limit, offset=offset
    )
    return [PostResponse.model_validate(p) for p in posts]


@router.get("/recommendations")
async def get_recommendations(
    media_type: str = Query(...),
    duration: float = Query(default=0),
    language: str = Query(default="en"),
    post_service: PostSvc = None,
) -> dict:
    from app.services.ai_service import AIService
    from app.config import get_settings
    s = get_settings()
    ai = AIService(s.OPENAI_API_KEY or None)
    recs = ai.recommend_platforms(media_type, duration, language)
    return {"recommendations": recs}


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: str, current_user: CurrentUser, post_service: PostSvc) -> PostResponse:
    post = await post_service.get_post(uuid.UUID(post_id), current_user.id)
    return PostResponse.model_validate(post)


@router.post("/{post_id}/retry")
async def retry_post(post_id: str, current_user: CurrentUser, post_service: PostSvc) -> dict:
    post = await post_service.get_post(uuid.UUID(post_id), current_user.id)
    post = await post_service.reset_failed_platforms(post)
    distribute_post.delay(str(post.id))
    failed_count = len(post.target_platforms)
    return {"message": f"Retrying {failed_count} platform(s)"}


@router.delete("/{post_id}", status_code=204)
async def delete_post(post_id: str, current_user: CurrentUser, post_service: PostSvc, media_service: MediaSvc):
    media_key = await post_service.delete_post(uuid.UUID(post_id), current_user.id)
    if media_key:
        await media_service.delete(media_key)
