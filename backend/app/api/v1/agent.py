"""Agent API routes — content feed, generation, and post management."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, desc

from app.api.deps import CurrentUser, DbSession, Cache
from app.models.models import ContentItem, ContentCategory, ContentInsight, GeneratedPost
from app.services.content_agent.hashtags import get_hashtags, format_hashtags
from app.services.content_agent.normalization import normalize_generated_content
from app.config import get_settings
from app.exceptions import NotFoundError

router = APIRouter(prefix="/agent", tags=["agent"])
settings = get_settings()


# ── Source-type mapping ──────────────────────────────────────────────────
_SOURCE_TYPE_PREFIXES = [
    ("nitter_",   "x"),
    ("linkedin_", "linkedin"),
    ("rss_",      "rss"),
    ("github_",   "github"),
    ("reddit_",   "reddit"),
    ("hn_",       "hackernews"),
    ("youtube_",  "youtube"),
]


def _source_type_from_key(source_key: str) -> str:
    """Derive a human-readable source type from the source_key prefix."""
    for prefix, source_type in _SOURCE_TYPE_PREFIXES:
        if source_key.startswith(prefix):
            return source_type
    return "other"


def _fallback_summary(item: ContentItem) -> str:
    """Return item.summary if present, else a cleaned snippet from raw_content."""
    if item.summary:
        return item.summary
    raw = (item.raw_content or "").strip()
    if not raw:
        return item.title or ""
    MAX_LEN = 250
    snippet = raw[:MAX_LEN].rsplit(" ", 1)[0] if len(raw) > MAX_LEN else raw
    return snippet + ("…" if len(raw) > MAX_LEN else "")


def _item_to_dict(item: ContentItem) -> dict:
    """Basic serializer (used by generate/posts endpoints)."""
    return {
        "id": str(item.id),
        "source_key": item.source_key,
        "source_label": item.source_label,
        "source_url": item.source_url,
        "source_type": _source_type_from_key(item.source_key),
        "title": item.title,
        "summary": _fallback_summary(item),
        "key_points": item.key_points or [],
        "raw_content": (item.raw_content or "")[:500],  # expose excerpt for frontend
        "category": item.category.value if item.category else "other",
        "relevance_score": item.relevance_score,
        "is_trending": item.is_trending,
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat(),
    }


def _enriched_item_dict(item: ContentItem, insight: ContentInsight | None) -> dict:
    """Enriched serializer — includes ContentInsight fields for the feed."""
    base = _item_to_dict(item)
    if insight:
        base["virality_score"] = insight.virality_score
        base["is_value_gap"] = insight.is_value_gap
        base["suggested_angle"] = insight.suggested_angle
        base["fact_check_passed"] = insight.fact_check_passed
        base["sentiment_breakdown"] = insight.sentiment_breakdown or {}
        base["broll_assets"] = insight.broll_assets or []
    else:
        base["virality_score"] = 0.0
        base["is_value_gap"] = False
        base["suggested_angle"] = None
        base["fact_check_passed"] = None
        base["sentiment_breakdown"] = {}
        base["broll_assets"] = []
    return base


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
    source_type: Optional[str] = Query(None, description="Filter by source type: x, linkedin, rss, github, reddit, hackernews, youtube"),
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

    # Source-type filter: match items whose source_key starts with the type prefix
    if source_type:
        prefix_map = {st: pfx for pfx, st in _SOURCE_TYPE_PREFIXES}
        prefix = prefix_map.get(source_type)
        if prefix:
            filters.append(ContentItem.source_key.startswith(prefix))

    # Outerjoin ContentInsight to enrich items with virality/sentiment/etc.
    query = (
        select(ContentItem, ContentInsight)
        .outerjoin(ContentInsight, ContentInsight.content_item_id == ContentItem.id)
        .where(and_(*filters))
        .order_by(
            desc(ContentItem.is_trending),
            desc(ContentInsight.virality_score),
            desc(ContentItem.relevance_score),
            desc(ContentItem.fetched_at),
        )
        .limit(limit).offset(offset)
    )
    result = await db.execute(query)
    rows = result.all()

    # Count query (uses same filters, just counts)
    count_q = (
        select(func.count(ContentItem.id))
        .outerjoin(ContentInsight, ContentInsight.content_item_id == ContentItem.id)
        .where(and_(*filters))
    )
    total = (await db.execute(count_q)).scalar() or 0

    trending_result = await db.execute(
        select(func.count(ContentItem.id)).where(and_(ContentItem.is_trending == True, ContentItem.fetched_at >= cutoff))
    )

    # Collect distinct source types for filter chips
    source_types_result = await db.execute(
        select(ContentItem.source_key)
        .where(and_(ContentItem.is_processed == True, ContentItem.fetched_at >= cutoff))
        .distinct()
    )
    source_keys = [row[0] for row in source_types_result.all()]
    available_source_types = sorted(set(_source_type_from_key(k) for k in source_keys) - {"other"})

    return JSONResponse({
        "items": [_enriched_item_dict(item, insight) for item, insight in rows],
        "total": total,
        "trending_count": trending_result.scalar() or 0,
        "categories": [c.value for c in ContentCategory],
        "source_types": available_source_types,
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
    try:
        item_uuid = uuid.UUID(str(item_id))
    except ValueError:
        return JSONResponse({"error": "invalid content_item_id"}, status_code=400)

    result = await db.execute(select(ContentItem).where(ContentItem.id == item_uuid))
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

        content = normalize_generated_content(
            await ai_generate(item_dict, plat, gemini_key=gemini_key, openai_key=openai_key)
        )
        curated = get_hashtags(item_dict["category"], plat.replace("_thread", "").replace("_script", ""), count=20)
        merged_hashtags = list(dict.fromkeys([*content["hashtags"], *curated]))[:20]

        post = GeneratedPost(
            content_item_id=item.id, user_id=current_user.id, platform=plat,
            hook=content["hook"], caption=content["caption"],
            hashtags=format_hashtags(merged_hashtags),
            call_to_action=content["call_to_action"],
            script_outline=content["script_outline"],
            thread_tweets=content["thread_tweets"],
            engagement_tips=content["engagement_tips"],
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
