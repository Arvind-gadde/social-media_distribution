"""Agent API routes — content feed, generation, and post management."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_

from app.api.deps import CurrentUser, DbSession, Cache
from app.models.models import ContentItem, ContentCategory, GeneratedPost
from app.services.content_agent.hashtags import get_hashtags, format_hashtags
from app.config import get_settings
from app.exceptions import NotFoundError

router = APIRouter(prefix="/agent", tags=["agent"])
settings = get_settings()


def _item_to_dict(item: ContentItem) -> dict:
    return {
        "id": str(item.id),
        "source_key": item.source_key,
        "source_label": item.source_label,
        "source_url": item.source_url,
        "title": item.title,
        "summary": item.summary,
        "key_points": item.key_points or [],
        "category": item.category.value if item.category else "other",
        "relevance_score": item.relevance_score,
        "is_trending": item.is_trending,
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat(),
    }


def _post_to_dict(post: GeneratedPost, item: ContentItem | None = None) -> dict:
    return {
        "id": str(post.id),
        "content_item_id": str(post.content_item_id),
        "platform": post.platform,
        "hook": post.hook,
        "caption": post.caption,
        "hashtags": post.hashtags or [],
        "call_to_action": post.call_to_action,
        "script_outline": post.script_outline,
        "thread_tweets": post.thread_tweets or [],
        "engagement_tips": post.engagement_tips or [],
        "created_at": post.created_at.isoformat(),
        "source_title": item.title if item else None,
        "source_url": item.source_url if item else None,
    }


@router.get("/feed")
async def get_feed(
    current_user: CurrentUser, db: DbSession,
    category: Optional[str] = Query(None),
    min_score: float = Query(0.4, ge=0.0, le=1.0),
    hours_back: int = Query(48, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    filters = [
        ContentItem.is_processed == True,
        ContentItem.relevance_score >= min_score,
        ContentItem.fetched_at >= cutoff,
    ]
    if category:
        try:
            filters.append(ContentItem.category == ContentCategory(category))
        except ValueError:
            pass

    result = await db.execute(
        select(ContentItem).where(and_(*filters))
        .order_by(ContentItem.is_trending.desc(), ContentItem.relevance_score.desc(), ContentItem.fetched_at.desc())
        .limit(limit).offset(offset)
    )
    items = result.scalars().all()
    count_result = await db.execute(select(func.count(ContentItem.id)).where(and_(*filters)))
    total = count_result.scalar() or 0
    trending_result = await db.execute(
        select(func.count(ContentItem.id)).where(and_(ContentItem.is_trending == True, ContentItem.fetched_at >= cutoff))
    )
    return JSONResponse({
        "items": [_item_to_dict(i) for i in items],
        "total": total,
        "trending_count": trending_result.scalar() or 0,
        "categories": [c.value for c in ContentCategory],
    })


@router.get("/stats")
async def get_stats(current_user: CurrentUser, db: DbSession) -> JSONResponse:
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    total_24h = await db.execute(select(func.count(ContentItem.id)).where(ContentItem.fetched_at >= cutoff_24h))
    top_stories = await db.execute(
        select(func.count(ContentItem.id)).where(and_(ContentItem.fetched_at >= cutoff_24h, ContentItem.relevance_score >= 0.7))
    )
    generated_7d = await db.execute(
        select(func.count(GeneratedPost.id)).where(and_(GeneratedPost.user_id == current_user.id, GeneratedPost.created_at >= cutoff_7d))
    )
    trending = await db.execute(
        select(func.count(ContentItem.id)).where(and_(ContentItem.fetched_at >= cutoff_24h, ContentItem.is_trending == True))
    )
    return JSONResponse({
        "items_collected_24h": total_24h.scalar() or 0,
        "top_stories_24h": top_stories.scalar() or 0,
        "content_generated_7d": generated_7d.scalar() or 0,
        "trending_now": trending.scalar() or 0,
    })


@router.post("/generate")
async def generate_content(body: dict, current_user: CurrentUser, db: DbSession) -> JSONResponse:
    item_id = body.get("content_item_id")
    platform = body.get("platform", "all")
    if not item_id:
        return JSONResponse({"error": "content_item_id required"}, status_code=400)

    result = await db.execute(select(ContentItem).where(ContentItem.id == uuid.UUID(str(item_id))))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("ContentItem", str(item_id))

    item_dict = {
        "id": str(item.id), "title": item.title,
        "raw_content": item.raw_content or "",
        "source_label": item.source_label, "source_url": item.source_url or "",
        "summary": item.summary or "", "key_points": item.key_points or [],
        "category": item.category.value if item.category else "other",
    }

    from app.services.content_agent.agent import generate_content as ai_generate

    platforms_to_generate = (
        ["instagram", "linkedin", "twitter_thread", "youtube_script"]
        if platform == "all" else [platform]
    )

    generated = {}
    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    for plat in platforms_to_generate:
        existing = await db.execute(
            select(GeneratedPost).where(and_(
                GeneratedPost.content_item_id == item.id,
                GeneratedPost.user_id == current_user.id,
                GeneratedPost.platform == plat,
            ))
        )
        existing_post = existing.scalar_one_or_none()
        if existing_post:
            generated[plat] = _post_to_dict(existing_post, item)
            continue

        content = await ai_generate(item_dict, plat, gemini_key=gemini_key, openai_key=openai_key)
        curated = get_hashtags(item_dict["category"], plat.replace("_thread", "").replace("_script", ""), count=20)
        ai_hashtags = content.get("hashtags") or []
        merged_hashtags = list(dict.fromkeys(ai_hashtags + curated))[:20]

        post = GeneratedPost(
            content_item_id=item.id, user_id=current_user.id, platform=plat,
            hook=content.get("hook", ""), caption=content.get("caption", ""),
            hashtags=format_hashtags(merged_hashtags),
            call_to_action=content.get("call_to_action", ""),
            script_outline=content.get("script_outline", ""),
            thread_tweets=content.get("thread_tweets", []),
            engagement_tips=content.get("engagement_tips", []),
        )
        db.add(post)
        await db.flush()
        await db.refresh(post)
        generated[plat] = _post_to_dict(post, item)

    await db.commit()
    return JSONResponse({
        "content_item": _item_to_dict(item),
        "generated": generated,
        "platforms_generated": list(generated.keys()),
    })


@router.get("/posts")
async def get_generated_posts(
    current_user: CurrentUser, db: DbSession,
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    filters = [GeneratedPost.user_id == current_user.id]
    if platform:
        filters.append(GeneratedPost.platform == platform)
    result = await db.execute(
        select(GeneratedPost, ContentItem)
        .join(ContentItem, GeneratedPost.content_item_id == ContentItem.id)
        .where(and_(*filters))
        .order_by(GeneratedPost.created_at.desc())
        .limit(limit).offset(offset)
    )
    rows = result.all()
    count_result = await db.execute(select(func.count(GeneratedPost.id)).where(and_(*filters)))
    return JSONResponse({"posts": [_post_to_dict(p, i) for p, i in rows], "total": count_result.scalar() or 0})


@router.delete("/posts/{post_id}")
async def delete_generated_post(post_id: str, current_user: CurrentUser, db: DbSession) -> JSONResponse:
    result = await db.execute(
        select(GeneratedPost).where(and_(GeneratedPost.id == uuid.UUID(post_id), GeneratedPost.user_id == current_user.id))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundError("GeneratedPost", post_id)
    await db.delete(post)
    await db.commit()
    return JSONResponse({"deleted": True})


@router.post("/run-collection")
async def trigger_collection(current_user: CurrentUser) -> JSONResponse:
    from app.workers.tasks import run_content_agent
    run_content_agent.delay(triggered_by="manual_api")
    return JSONResponse({"status": "triggered", "message": "Orchestrated pipeline started in background"})
