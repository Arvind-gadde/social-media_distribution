"""News API — Phase 15 Req 6.

Niche-aware news feed backed by NewsFetcher. Items are ephemeral (fetched per
request, lightly cached in Redis); creating content from an article spins up a
ContentProject in IDEA status with the article URL recorded on rationale.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Cache, CurrentUser, CurrentWorkspace, DbSession
from app.domains.control.models import Niche, WorkspaceNiche
from app.domains.execution.models import ContentProject, ProjectStatus
from app.services.news.news_fetcher import NewsFetcher

router = APIRouter(prefix="/news", tags=["news"])


class NewsArticleOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    url: str
    author: str | None = None
    published_at: str | None = None
    source: str | None = None
    source_url: str | None = None
    thumbnail_url: str | None = None
    relevance_score: float = 0.5


class NewsListResponse(BaseModel):
    items: list[NewsArticleOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    niche: str | None = None


class CreateFromNewsRequest(BaseModel):
    title: str
    description: str | None = None
    url: str


def _article_id(article: dict[str, Any]) -> str:
    raw = (article.get("url") or article.get("title") or "").encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _to_out(article: dict[str, Any]) -> NewsArticleOut:
    return NewsArticleOut(
        id=_article_id(article),
        title=article.get("title", "Untitled"),
        description=article.get("description"),
        url=article.get("url", ""),
        author=article.get("author"),
        published_at=article.get("published_at"),
        source=article.get("source"),
        source_url=article.get("source_url"),
        thumbnail_url=article.get("thumbnail_url"),
        relevance_score=float(article.get("relevance_score", 0.5)),
    )


async def _resolve_workspace_niche(db, workspace_id: uuid.UUID) -> tuple[str, list[str]]:
    """Return (niche_slug, keywords) for the workspace. Defaults to 'tech' when missing."""
    row = (
        await db.execute(
            select(WorkspaceNiche, Niche)
            .join(Niche, WorkspaceNiche.niche_id == Niche.id)
            .where(WorkspaceNiche.workspace_id == workspace_id)
            .order_by(WorkspaceNiche.is_primary.desc())
            .limit(1)
        )
    ).first()
    if not row:
        return "tech", []
    _, niche = row
    return niche.slug, list(niche.keywords or [])


@router.get("", response_model=NewsListResponse)
async def list_news(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    cache: Cache,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    niche: str | None = None,
    relevance_threshold: Annotated[float, Query(ge=0.0, le=1.0)] = 0.3,
) -> NewsListResponse:
    resolved_niche, keywords = await _resolve_workspace_niche(db, workspace.id)
    niche_slug = niche or resolved_niche

    cache_key = f"news:{niche_slug}:{round(relevance_threshold, 2)}"
    articles = await cache.get(cache_key)
    if not articles:
        fetcher = NewsFetcher()
        articles = await fetcher.fetch_and_score_news(
            niche=niche_slug,
            niche_keywords=keywords,
            max_items=60,
            min_relevance=relevance_threshold,
        )
        await cache.set(cache_key, articles, ttl_seconds=600)

    total = len(articles)
    start = (page - 1) * page_size
    page_items = articles[start : start + page_size]
    return NewsListResponse(
        items=[_to_out(a) for a in page_items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(start + page_size) < total,
        niche=niche_slug,
    )


@router.get("/{article_id}", response_model=NewsArticleOut)
async def get_news_article(
    article_id: str,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    cache: Cache,
) -> NewsArticleOut:
    resolved_niche, _ = await _resolve_workspace_niche(db, workspace.id)
    cache_key_prefix = f"news:{resolved_niche}:"
    # Probe the most common cached threshold first.
    for threshold in (0.3, 0.5, 0.7, 0.0):
        cached = await cache.get(f"{cache_key_prefix}{round(threshold, 2)}")
        if cached:
            for article in cached:
                if _article_id(article) == article_id:
                    return _to_out(article)
    raise HTTPException(status_code=404, detail="Article not found (refetch list first)")


@router.post("/create-content", response_model=dict[str, Any], status_code=201)
async def create_content_from_news(
    body: CreateFromNewsRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> dict[str, Any]:
    project = ContentProject(
        workspace_id=workspace.id,
        title=body.title[:500],
        description=body.description,
        content_type="post",
        status=ProjectStatus.IDEA,
        ai_rationale=json.dumps({"source": "news", "url": body.url}),
        created_by=user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return {
        "project_id": str(project.id),
        "status": project.status.value,
        "created_at": project.created_at.isoformat(),
    }
