"""Agent API routes — content feed, generation, and pipeline trigger.

v2: Workspace-scoped feed using SourceDocument + SourceDocumentInsight.
Legacy endpoints preserved for backward compatibility.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, desc

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, Cache
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
    for prefix, source_type in _SOURCE_TYPE_PREFIXES:
        if source_key.startswith(prefix):
            return source_type
    return "other"


def _doc_to_dict(doc) -> dict:
    """Serialize a SourceDocument for the feed."""
    return {
        "id": str(doc.id),
        "source_key": doc.source_key,
        "source_label": doc.source_label,
        "source_url": doc.source_url,
        "source_type": _source_type_from_key(doc.source_key),
        "title": doc.title,
        "summary": doc.summary or (doc.raw_content or "")[:250],
        "key_points": doc.key_points or [],
        "raw_content": (doc.raw_content or "")[:500],
        "category": doc.category if doc.category else "other",
        "relevance_score": doc.relevance_score,
        "is_trending": doc.is_trending,
        "author": doc.author,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "fetched_at": doc.fetched_at.isoformat() if doc.fetched_at else None,
    }


def _enriched_doc_dict(doc, insight) -> dict:
    """Enriched serializer — includes SourceDocumentInsight fields."""
    base = _doc_to_dict(doc)
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


@router.get("/feed")
async def get_feed(
    current_user: CurrentUser,
    db: DbSession,
    category: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    min_score: float = Query(0.4, ge=0.0, le=1.0),
    hours_back: int = Query(48, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """Content intelligence feed using SourceDocument + SourceDocumentInsight."""
    from app.domains.intelligence.models import SourceDocument, SourceDocumentInsight

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    filters = [
        SourceDocument.is_processed == True,
        SourceDocument.relevance_score >= min_score,
        SourceDocument.fetched_at >= cutoff,
    ]
    if category:
        filters.append(SourceDocument.category == category)

    if source_type:
        prefix_map = {st: pfx for pfx, st in _SOURCE_TYPE_PREFIXES}
        prefix = prefix_map.get(source_type)
        if prefix:
            filters.append(SourceDocument.source_key.startswith(prefix))

    query = (
        select(SourceDocument, SourceDocumentInsight)
        .outerjoin(
            SourceDocumentInsight,
            SourceDocumentInsight.source_document_id == SourceDocument.id,
        )
        .where(and_(*filters))
        .order_by(
            desc(SourceDocument.is_trending),
            desc(SourceDocumentInsight.virality_score),
            desc(SourceDocument.relevance_score),
            desc(SourceDocument.fetched_at),
        )
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    rows = result.all()

    count_q = (
        select(func.count(SourceDocument.id))
        .outerjoin(
            SourceDocumentInsight,
            SourceDocumentInsight.source_document_id == SourceDocument.id,
        )
        .where(and_(*filters))
    )
    total = (await db.execute(count_q)).scalar() or 0

    trending_result = await db.execute(
        select(func.count(SourceDocument.id)).where(
            and_(SourceDocument.is_trending == True, SourceDocument.fetched_at >= cutoff)
        )
    )

    source_types_result = await db.execute(
        select(SourceDocument.source_key)
        .where(and_(SourceDocument.is_processed == True, SourceDocument.fetched_at >= cutoff))
        .distinct()
    )
    source_keys = [row[0] for row in source_types_result.all()]
    available_source_types = sorted(set(_source_type_from_key(k) for k in source_keys) - {"other"})

    return JSONResponse({
        "items": [_enriched_doc_dict(doc, insight) for doc, insight in rows],
        "total": total,
        "trending_count": trending_result.scalar() or 0,
        "categories": ["tech", "ai", "finance", "crypto", "dev_tools", "startup", "open_source", "science", "other"],
        "source_types": available_source_types,
    })


@router.get("/stats")
async def get_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """Agent pipeline stats."""
    from app.domains.intelligence.models import SourceDocument, AgentRun
    from app.domains.execution.models import ContentVariant

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)

    total_24h = await db.execute(
        select(func.count(SourceDocument.id)).where(SourceDocument.fetched_at >= cutoff_24h)
    )
    top_stories = await db.execute(
        select(func.count(SourceDocument.id)).where(
            and_(SourceDocument.fetched_at >= cutoff_24h, SourceDocument.relevance_score >= 0.7)
        )
    )
    generated_7d = await db.execute(
        select(func.count(ContentVariant.id)).where(ContentVariant.created_at >= cutoff_7d)
    )
    trending = await db.execute(
        select(func.count(SourceDocument.id)).where(
            and_(SourceDocument.fetched_at >= cutoff_24h, SourceDocument.is_trending == True)
        )
    )

    return JSONResponse({
        "items_collected_24h": total_24h.scalar() or 0,
        "top_stories_24h": top_stories.scalar() or 0,
        "content_generated_7d": generated_7d.scalar() or 0,
        "trending_now": trending.scalar() or 0,
    })


@router.post("/generate")
async def generate_content(
    body: dict,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Generate content for a source document using the AI pipeline."""
    from app.domains.intelligence.models import SourceDocument
    from app.domains.execution.models import (
        ContentProject, ContentVariant, ProjectStatus, AuthoringSource,
    )
    from app.services.content_agent.agent import generate_content as ai_generate
    from app.services.content_agent.hashtags import get_hashtags, format_hashtags
    from app.services.content_agent.normalization import normalize_generated_content

    item_id = body.get("content_item_id") or body.get("source_document_id")
    platform = body.get("platform", "all")
    if not item_id:
        return JSONResponse({"error": "source_document_id required"}, status_code=400)

    try:
        item_uuid = uuid.UUID(str(item_id))
    except ValueError:
        return JSONResponse({"error": "invalid source_document_id"}, status_code=400)

    result = await db.execute(select(SourceDocument).where(SourceDocument.id == item_uuid))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("SourceDocument", str(item_id))

    item_dict = {
        "id": str(doc.id),
        "title": doc.title,
        "raw_content": doc.raw_content or "",
        "source_label": doc.source_label,
        "source_url": doc.source_url or "",
        "summary": doc.summary or "",
        "key_points": doc.key_points or [],
        "category": doc.category or "other",
    }

    # Create a ContentProject for this generation
    project = ContentProject(
        workspace_id=workspace.id,
        title=doc.title,
        description=doc.summary,
        status=ProjectStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()

    platforms_to_generate = (
        ["instagram", "linkedin", "twitter", "youtube"]
        if platform == "all" else [platform]
    )

    generated = {}
    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    for plat in platforms_to_generate:
        # Map new platform names to old ones for backward compat
        old_plat = plat
        if plat == "twitter":
            old_plat = "twitter_thread"
        elif plat == "youtube":
            old_plat = "youtube_script"

        content = normalize_generated_content(
            await ai_generate(item_dict, old_plat, gemini_key=gemini_key, openai_key=openai_key)
        )
        curated = get_hashtags(
            item_dict["category"],
            plat.replace("_thread", "").replace("_script", ""),
            count=20,
        )
        merged_hashtags = list(dict.fromkeys([*content["hashtags"], *curated]))[:20]

        variant = ContentVariant(
            workspace_id=workspace.id,
            project_id=project.id,
            source_document_id=doc.id,
            target_platform=plat,
            hook=content["hook"],
            caption=content["caption"],
            hashtags=merged_hashtags,
            call_to_action=content["call_to_action"],
            script_outline=content["script_outline"],
            thread_tweets=content["thread_tweets"],
            engagement_tips=content["engagement_tips"],
            authoring_source=AuthoringSource.ASSISTANT,
            prompt_version="v2.0",
        )
        db.add(variant)
        await db.flush()
        await db.refresh(variant)

        generated[plat] = {
            "id": str(variant.id),
            "project_id": str(project.id),
            "platform": plat,
            "hook": variant.hook,
            "caption": variant.caption,
            "hashtags": variant.hashtags or [],
            "call_to_action": variant.call_to_action,
            "script_outline": variant.script_outline,
            "thread_tweets": variant.thread_tweets or [],
            "engagement_tips": variant.engagement_tips or [],
            "created_at": variant.created_at.isoformat(),
        }

    return JSONResponse({
        "source_document": _doc_to_dict(doc),
        "project_id": str(project.id),
        "generated": generated,
        "platforms_generated": list(generated.keys()),
    })


@router.get("/posts")
async def get_generated_posts(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """List generated content variants for the workspace."""
    from app.domains.execution.models import ContentVariant

    filters = [ContentVariant.workspace_id == workspace.id]
    if platform:
        filters.append(ContentVariant.target_platform == platform)

    result = await db.execute(
        select(ContentVariant)
        .where(and_(*filters))
        .order_by(ContentVariant.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    variants = result.scalars().all()

    count_result = await db.execute(
        select(func.count(ContentVariant.id)).where(and_(*filters))
    )

    return JSONResponse({
        "posts": [
            {
                "id": str(v.id),
                "project_id": str(v.project_id),
                "platform": v.target_platform,
                "hook": v.hook,
                "caption": v.caption,
                "hashtags": v.hashtags or [],
                "call_to_action": v.call_to_action,
                "script_outline": v.script_outline,
                "thread_tweets": v.thread_tweets or [],
                "engagement_tips": v.engagement_tips or [],
                "created_at": v.created_at.isoformat(),
            }
            for v in variants
        ],
        "total": count_result.scalar() or 0,
    })


@router.delete("/posts/{post_id}")
async def delete_generated_post(
    post_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Delete a content variant."""
    from app.domains.execution.models import ContentVariant
    from sqlalchemy import delete

    result = await db.execute(
        delete(ContentVariant).where(
            and_(
                ContentVariant.id == uuid.UUID(post_id),
                ContentVariant.workspace_id == workspace.id,
            )
        )
    )
    if result.rowcount == 0:
        raise NotFoundError("ContentVariant", post_id)
    return JSONResponse({"deleted": True})


@router.post("/run-collection")
async def trigger_collection(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
) -> JSONResponse:
    """Trigger the orchestrated pipeline for the current workspace."""
    from app.workers.tasks import run_content_agent

    run_content_agent.delay(
        workspace_id=str(workspace.id),
        actor_id=str(current_user.id),
        trigger="manual",
    )
    return JSONResponse({
        "status": "triggered",
        "message": "Orchestrated pipeline started for your workspace",
        "workspace_id": str(workspace.id),
    })
