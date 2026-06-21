"""Content API — /content-projects + /ideas, matching frontend api-client paths.

Wraps ContentProject for CRUD + publish/schedule + virality analysis.
Idea endpoints generate ephemeral suggestions via the LLM provider.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, get_llm_provider
from app.domains.execution.models import (
    ContentProject,
    ContentVariant,
    ProjectStatus,
    PublishJob,
    PublishStatus,
)
from app.domains.control.models import SocialAccount, TokenStatus
from app.integrations.llm.provider import TaskType

# ─── Two routers in one file ────────────────────────────────────────────────────
projects_router = APIRouter(prefix="/content-projects", tags=["content"])
ideas_router = APIRouter(prefix="/ideas", tags=["content"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class ContentItemOut(BaseModel):
    id: uuid.UUID
    title: str
    caption: str | None = None
    script: str | None = None
    content_type: str | None = None
    status: str
    platforms: list[str] = Field(default_factory=list)
    scheduled_at: str | None = None
    published_at: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    thumbnail_url: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_saves: int = 0
    engagement_rate: float = 0.0
    reach: int = 0
    impressions: int = 0
    ai_generated: bool = False
    ai_score: float | None = None
    created_at: str
    updated_at: str


class PaginatedContent(BaseModel):
    items: list[ContentItemOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class ContentCreate(BaseModel):
    title: str | None = None
    caption: str | None = None
    script: str | None = None
    content_type: str
    platforms: list[str] = Field(default_factory=list)
    status: str | None = None
    scheduled_at: datetime | None = None
    hashtags: list[str] | None = None
    media_urls: list[str] | None = None
    thumbnail_url: str | None = None


class ContentUpdate(BaseModel):
    title: str | None = None
    caption: str | None = None
    script: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    hashtags: list[str] | None = None
    platforms: list[str] | None = None


class ScheduleRequest(BaseModel):
    scheduled_at: datetime


class AnalyzeResponse(BaseModel):
    virality_score: float
    strengths: list[str]
    improvements: list[str]
    predicted_views: int
    predicted_engagement: float


# ═══════════════════════════════════════════════════════════════════════════════
# MAPPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _aggregate_variant_metrics(variants: list[ContentVariant]) -> dict[str, Any]:
    if not variants:
        return {
            "caption": None,
            "platforms": [],
            "hashtags": [],
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "total_saves": 0,
            "engagement_rate": 0.0,
        }
    platforms = sorted({v.target_platform for v in variants if v.target_platform})
    hashtags: list[str] = []
    for v in variants:
        if v.hashtags:
            hashtags.extend(v.hashtags)
    caption = next((v.caption for v in variants if v.caption), None)
    n = len(variants)
    return {
        "caption": caption,
        "platforms": platforms,
        "hashtags": sorted(set(hashtags)),
        "total_views": sum(v.total_views for v in variants),
        "total_likes": sum(v.total_likes for v in variants),
        "total_comments": sum(v.total_comments for v in variants),
        "total_shares": sum(v.total_shares for v in variants),
        "total_saves": sum(v.total_saves for v in variants),
        "engagement_rate": sum(v.engagement_rate for v in variants) / n if n else 0.0,
    }


async def _load_variants(db, project_id: uuid.UUID) -> list[ContentVariant]:
    return list(
        (
            await db.execute(
                select(ContentVariant).where(ContentVariant.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )


# Statuses for which a publish job is "in flight or done" — used to avoid
# enqueuing a duplicate when publish/schedule is called more than once.
_ACTIVE_JOB_STATUSES = (
    PublishStatus.QUEUED,
    PublishStatus.LEASED,
    PublishStatus.RUNNING,
    PublishStatus.AWAITING_APPROVAL,
    PublishStatus.COMPLETED,
)


async def _enqueue_publish_jobs(
    db,
    project: ContentProject,
    variants: list[ContentVariant],
    scheduled_at: datetime,
) -> int:
    """Create QUEUED PublishJobs for each (variant, connected account) pair.

    This is what feeds the Celery publish pipeline — without it, marking a
    project published/scheduled does nothing. Skips platforms with no valid,
    active connected account and pairs that already have an in-flight/done job.
    Returns the number of jobs created.
    """
    created = 0
    for variant in variants:
        accounts = (
            await db.execute(
                select(SocialAccount).where(
                    SocialAccount.workspace_id == project.workspace_id,
                    SocialAccount.platform == variant.target_platform,
                    SocialAccount.is_active == True,
                    SocialAccount.token_status == TokenStatus.VALID,
                )
            )
        ).scalars().all()

        for account in accounts:
            existing = (
                await db.execute(
                    select(PublishJob.id)
                    .where(
                        PublishJob.content_variant_id == variant.id,
                        PublishJob.social_account_id == account.id,
                        PublishJob.status.in_(_ACTIVE_JOB_STATUSES),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing:
                continue

            db.add(
                PublishJob(
                    workspace_id=project.workspace_id,
                    content_variant_id=variant.id,
                    social_account_id=account.id,
                    target_platform=variant.target_platform,
                    scheduled_at=scheduled_at,
                    status=PublishStatus.QUEUED,
                    idempotency_key=f"{variant.id}:{account.id}:{int(scheduled_at.timestamp())}",
                )
            )
            created += 1

    await db.flush()
    return created


def _to_item(project: ContentProject, variants: list[ContentVariant]) -> ContentItemOut:
    agg = _aggregate_variant_metrics(variants)
    platforms = agg["platforms"] or (project.target_platforms or [])
    return ContentItemOut(
        id=project.id,
        title=project.title,
        caption=agg["caption"],
        script=None,
        content_type=project.content_type,
        status=project.status.value,
        platforms=platforms,
        scheduled_at=project.scheduled_at.isoformat() if project.scheduled_at else None,
        published_at=project.published_at.isoformat() if project.published_at else None,
        media_urls=[],
        thumbnail_url=None,
        hashtags=agg["hashtags"],
        total_views=agg["total_views"],
        total_likes=agg["total_likes"],
        total_comments=agg["total_comments"],
        total_shares=agg["total_shares"],
        total_saves=agg["total_saves"],
        engagement_rate=agg["engagement_rate"],
        ai_generated=any(v.authoring_source.value == "assistant" for v in variants),
        ai_score=project.virality_score,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT PROJECTS
# ═══════════════════════════════════════════════════════════════════════════════


@projects_router.get("", response_model=PaginatedContent)
async def list_content(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = None,
    content_type: str | None = None,
    platform: str | None = None,
    search: str | None = None,
) -> PaginatedContent:
    q = select(ContentProject).where(
        ContentProject.workspace_id == workspace.id,
        ContentProject.deleted_at.is_(None),
    )
    if status:
        try:
            q = q.where(ContentProject.status == ProjectStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if content_type:
        q = q.where(ContentProject.content_type == content_type)
    if platform:
        q = q.where(ContentProject.target_platforms.any(platform))
    if search:
        like = f"%{search}%"
        q = q.where(ContentProject.title.ilike(like))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(ContentProject.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    projects = list((await db.execute(q)).scalars().all())

    items: list[ContentItemOut] = []
    for p in projects:
        variants = await _load_variants(db, p.id)
        items.append(_to_item(p, variants))

    return PaginatedContent(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < int(total),
    )


@projects_router.post("", response_model=ContentItemOut, status_code=201)
async def create_content(
    body: ContentCreate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    try:
        status = ProjectStatus(body.status) if body.status else ProjectStatus.DRAFT
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    project = ContentProject(
        workspace_id=workspace.id,
        title=body.title or "Untitled",
        description=None,
        content_type=body.content_type,
        status=status,
        target_platforms=body.platforms or None,
        scheduled_at=body.scheduled_at,
        created_by=user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    if body.caption or body.hashtags:
        for platform in body.platforms or [""]:
            db.add(
                ContentVariant(
                    workspace_id=workspace.id,
                    project_id=project.id,
                    target_platform=platform or "generic",
                    caption=body.caption,
                    hashtags=body.hashtags,
                )
            )
        await db.flush()

    variants = await _load_variants(db, project.id)
    return _to_item(project, variants)


async def _load_project(db, workspace_id: uuid.UUID, project_id: uuid.UUID) -> ContentProject:
    p = (
        await db.execute(
            select(ContentProject).where(
                ContentProject.id == project_id,
                ContentProject.workspace_id == workspace_id,
                ContentProject.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Content not found")
    return p


@projects_router.get("/{project_id}", response_model=ContentItemOut)
async def get_content_item(
    project_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    p = await _load_project(db, workspace.id, project_id)
    variants = await _load_variants(db, p.id)
    return _to_item(p, variants)


@projects_router.patch("/{project_id}", response_model=ContentItemOut)
async def update_content_item(
    project_id: uuid.UUID,
    body: ContentUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    p = await _load_project(db, workspace.id, project_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data:
        try:
            p.status = ProjectStatus(data.pop("status"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if "platforms" in data:
        p.target_platforms = data.pop("platforms") or None
    for k in ("title", "scheduled_at"):
        if k in data:
            setattr(p, k, data.pop(k))
    # caption/script/hashtags live on variants — keep this thin and only update the first.
    if any(k in data for k in ("caption", "script", "hashtags")):
        variants = await _load_variants(db, p.id)
        if variants:
            v = variants[0]
            if "caption" in data:
                v.caption = data["caption"]
            if "script" in data:
                v.script = data["script"]
            if "hashtags" in data:
                v.hashtags = data["hashtags"]
    await db.flush()
    await db.refresh(p)
    variants = await _load_variants(db, p.id)
    return _to_item(p, variants)


@projects_router.delete("/{project_id}", status_code=204, response_model=None)
async def delete_content_item(
    project_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> None:
    p = await _load_project(db, workspace.id, project_id)
    p.deleted_at = datetime.now(timezone.utc)
    await db.flush()


@projects_router.post("/{project_id}/publish", response_model=ContentItemOut)
async def publish_content(
    project_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    p = await _load_project(db, workspace.id, project_id)
    variants = await _load_variants(db, p.id)
    # Enqueue publish jobs NOW so the Celery pipeline picks them up immediately.
    await _enqueue_publish_jobs(db, p, variants, datetime.now(timezone.utc))
    p.status = ProjectStatus.PUBLISHED
    p.published_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(p)
    return _to_item(p, variants)


@projects_router.post("/{project_id}/schedule", response_model=ContentItemOut)
async def schedule_content(
    project_id: uuid.UUID,
    body: ScheduleRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    p = await _load_project(db, workspace.id, project_id)
    p.status = ProjectStatus.SCHEDULED
    p.scheduled_at = body.scheduled_at
    variants = await _load_variants(db, p.id)
    # Enqueue jobs at the scheduled time; the beat task picks them up when due.
    await _enqueue_publish_jobs(db, p, variants, body.scheduled_at)
    await db.flush()
    await db.refresh(p)
    return _to_item(p, variants)


@projects_router.post("/{project_id}/analyze", response_model=AnalyzeResponse)
async def analyze_content(
    project_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> AnalyzeResponse:
    """Virality analysis using the LLM provider. Result is persisted on the project."""
    p = await _load_project(db, workspace.id, project_id)
    variants = await _load_variants(db, p.id)
    agg = _aggregate_variant_metrics(variants)

    llm = await get_llm_provider()
    prompt = (
        "Analyze this content for virality. Return JSON with fields: "
        "virality_score (0-1 float), strengths (list of strings), improvements (list of strings), "
        "predicted_views (int), predicted_engagement (0-1 float).\n\n"
        f"Title: {p.title}\n"
        f"Type: {p.content_type or 'unknown'}\n"
        f"Caption: {agg['caption'] or ''}\n"
        f"Hashtags: {', '.join(agg['hashtags']) or 'none'}\n"
        f"Platforms: {', '.join(agg['platforms']) or 'unspecified'}\n"
    )
    try:
        resp = await llm.complete(
            task_type=TaskType.ANALYSIS if hasattr(TaskType, "ANALYSIS") else TaskType.GENERATION,
            messages=[
                {"role": "system", "content": "You are an expert social media analyst."},
                {"role": "user", "content": prompt},
            ],
            workspace_id=workspace.id,
            json_mode=True,
        )
        data = json.loads(resp.content)
    except Exception:
        data = {
            "virality_score": 0.5,
            "strengths": [],
            "improvements": [],
            "predicted_views": 0,
            "predicted_engagement": 0.0,
        }

    score = float(data.get("virality_score", 0.5))
    p.virality_score = score
    p.ai_rationale = json.dumps(
        {"strengths": data.get("strengths", []), "improvements": data.get("improvements", [])}
    )
    await db.flush()

    return AnalyzeResponse(
        virality_score=score,
        strengths=list(data.get("strengths", []))[:10],
        improvements=list(data.get("improvements", []))[:10],
        predicted_views=int(data.get("predicted_views", 0) or 0),
        predicted_engagement=float(data.get("predicted_engagement", 0.0) or 0.0),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# IDEAS  (ephemeral — LLM-generated, not persisted)
# ═══════════════════════════════════════════════════════════════════════════════


class ContentIdeaOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    hook: str | None = None
    content_type: str
    platforms: list[str] = Field(default_factory=list)
    hashtags: list[str] | None = None
    estimated_virality: float = 0.5
    ai_rationale: str | None = None
    source: str = "agent"
    status: str = "new"
    created_at: str


class PaginatedIdeas(BaseModel):
    items: list[ContentIdeaOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class GenerateIdeasRequest(BaseModel):
    count: int = Field(5, ge=1, le=20)
    topic: str | None = Field(default=None, max_length=300)
    niche: str | None = Field(default=None, max_length=80)


class IdeaStatusUpdate(BaseModel):
    status: str


@ideas_router.get("", response_model=PaginatedIdeas)
async def list_ideas(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = None,
    min_virality: float | None = None,
) -> PaginatedIdeas:
    """Ideas surface as ContentProjects in IDEA status."""
    q = select(ContentProject).where(
        ContentProject.workspace_id == workspace.id,
        ContentProject.status == ProjectStatus.IDEA,
        ContentProject.deleted_at.is_(None),
    )
    if min_virality is not None:
        q = q.where(ContentProject.virality_score >= min_virality)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(ContentProject.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    rows = list((await db.execute(q)).scalars().all())

    items = [
        ContentIdeaOut(
            id=p.id,
            title=p.title,
            description=p.description,
            hook=None,
            content_type=p.content_type or "post",
            platforms=p.target_platforms or [],
            hashtags=None,
            estimated_virality=p.virality_score or 0.5,
            ai_rationale=p.ai_rationale,
            source="agent",
            status="new",
            created_at=p.created_at.isoformat(),
        )
        for p in rows
    ]
    return PaginatedIdeas(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < int(total),
    )


@ideas_router.post("/generate", response_model=list[ContentIdeaOut])
async def generate_ideas(
    body: GenerateIdeasRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> list[ContentIdeaOut]:
    """Generate N ideas via LLM and persist them as ContentProjects in IDEA status."""
    from app.services.content_agent.niche_resolver import get_primary_niche_slug

    llm = await get_llm_provider()

    # Niche-aware: anchor ideas to the workspace's primary niche (or an explicit
    # override) plus an optional topic, so suggestions are tailored — not generic.
    niche = body.niche or await get_primary_niche_slug(db, workspace.id)
    context_bits: list[str] = []
    if niche:
        context_bits.append(f"creator niche: {niche}")
    if body.topic:
        context_bits.append(f"topic focus: {body.topic}")
    context_line = (
        " Tailor every idea to this creator — " + "; ".join(context_bits) + "."
        if context_bits
        else ""
    )

    system_prompt = (
        "You are a creative social-media content strategist who specializes in "
        "niche-native, platform-aware viral content. Always return strict JSON."
    )
    prompt = (
        f"Generate {body.count} viral social media content ideas.{context_line} "
        "Return JSON object {\"ideas\": [{title, description, hook, content_type, "
        "platforms (array), hashtags (array), estimated_virality (0-1)}]}."
    )
    try:
        resp = await llm.complete(
            task_type=TaskType.GENERATION,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            workspace_id=workspace.id,
            json_mode=True,
            cache_system_prompt=True,
        )
        data = json.loads(resp.content)
        raw_ideas = data.get("ideas") if isinstance(data, dict) else data
        if not isinstance(raw_ideas, list):
            raw_ideas = []
    except Exception:
        raw_ideas = []

    out: list[ContentIdeaOut] = []
    for raw in raw_ideas[: body.count]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "Untitled idea"))[:500]
        platforms = raw.get("platforms") or []
        if not isinstance(platforms, list):
            platforms = []
        score = float(raw.get("estimated_virality", 0.5) or 0.5)

        project = ContentProject(
            workspace_id=workspace.id,
            title=title,
            description=raw.get("description"),
            content_type=raw.get("content_type") or "post",
            status=ProjectStatus.IDEA,
            target_platforms=[str(p) for p in platforms] or None,
            virality_score=score,
            ai_rationale=raw.get("hook"),
            created_by=user.id,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

        out.append(
            ContentIdeaOut(
                id=project.id,
                title=project.title,
                description=project.description,
                hook=raw.get("hook"),
                content_type=project.content_type or "post",
                platforms=project.target_platforms or [],
                hashtags=raw.get("hashtags") if isinstance(raw.get("hashtags"), list) else None,
                estimated_virality=score,
                ai_rationale=project.ai_rationale,
                source="agent",
                status="new",
                created_at=project.created_at.isoformat(),
            )
        )
    return out


@ideas_router.patch("/{idea_id}/status", response_model=ContentIdeaOut)
async def update_idea_status(
    idea_id: uuid.UUID,
    body: IdeaStatusUpdate,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentIdeaOut:
    p = await _load_project(db, workspace.id, idea_id)
    mapping = {
        "saved": ProjectStatus.IDEA,
        "in_progress": ProjectStatus.DRAFT,
        "used": ProjectStatus.PUBLISHED,
        "dismissed": ProjectStatus.ARCHIVED,
    }
    if body.status not in mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid idea status. Allowed: {sorted(mapping)}",
        )
    p.status = mapping[body.status]
    await db.flush()
    await db.refresh(p)
    return ContentIdeaOut(
        id=p.id,
        title=p.title,
        description=p.description,
        hook=None,
        content_type=p.content_type or "post",
        platforms=p.target_platforms or [],
        hashtags=None,
        estimated_virality=p.virality_score or 0.5,
        ai_rationale=p.ai_rationale,
        source="agent",
        status=body.status,
        created_at=p.created_at.isoformat(),
    )


@ideas_router.post("/{idea_id}/create-content", response_model=ContentItemOut)
async def create_content_from_idea(
    idea_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> ContentItemOut:
    p = await _load_project(db, workspace.id, idea_id)
    if p.status == ProjectStatus.IDEA:
        p.status = ProjectStatus.DRAFT
    await db.flush()
    await db.refresh(p)
    variants = await _load_variants(db, p.id)
    return _to_item(p, variants)
