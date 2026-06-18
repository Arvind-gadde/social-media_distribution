"""Posts routes — upload, list, get, retry, delete."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, Query
from fastapi.responses import JSONResponse
from app.api.deps import CurrentUser, MediaSvc, DbSession
from app.exceptions import ValidationError
from app.domains.execution.models import PublishStatus
from app.schemas.schemas import PostResponse
from app.workers.tasks import distribute_post

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostResponse, status_code=201)
async def upload_post(
    current_user: CurrentUser,
    db: DbSession,
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

    from app.repositories.repositories import PostRepository
    repo = PostRepository(db)
    post = await repo.create(
        user_id=current_user.id,
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
    db: DbSession,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PostResponse]:
    from app.repositories.repositories import PostRepository
    status_enum = PublishStatus(status) if status else None
    repo = PostRepository(db)
    posts = await repo.list_for_user(
        current_user.id, status=status_enum, limit=limit, offset=offset
    )
    return [PostResponse.model_validate(p) for p in posts]


@router.get("/recommendations")
async def get_recommendations(
    media_type: str = Query(...),
    duration: float = Query(default=0),
    language: str = Query(default="en"),
) -> dict:
    from app.services.ai_service import AIService
    from app.config import get_settings
    s = get_settings()
    ai = AIService(s.OPENAI_API_KEY or None)
    recs = ai.recommend_platforms(media_type, duration, language)
    return {"recommendations": recs}


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: str, current_user: CurrentUser, db: DbSession) -> PostResponse:
    from app.repositories.repositories import PostRepository
    repo = PostRepository(db)
    post = await repo.get_by_id(uuid.UUID(post_id))
    if not post or post.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)


@router.post("/{post_id}/retry")
async def retry_post(post_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    from app.repositories.repositories import PostRepository
    repo = PostRepository(db)
    post = await repo.get_by_id(uuid.UUID(post_id))
    if not post or post.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    # Reset failed platforms
    post.status = PublishStatus.QUEUED
    await db.commit()
    distribute_post.delay(str(post.id))
    failed_count = len(post.target_platforms)
    return {"message": f"Retrying {failed_count} platform(s)"}


@router.delete("/{post_id}", status_code=204, response_model=None)
async def delete_post(post_id: str, current_user: CurrentUser, db: DbSession, media_service: MediaSvc):
    from app.repositories.repositories import PostRepository
    repo = PostRepository(db)
    post = await repo.get_by_id(uuid.UUID(post_id))
    if not post or post.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    media_key = post.media_key
    await repo.delete(post.id)
    if media_key:
        await media_service.delete(media_key)
