"""Content Projects API — Content lifecycle from idea to published.

Routes:
  GET    /content/projects             List projects
  POST   /content/projects             Create a project
  GET    /content/projects/{id}        Get project with variants
  PATCH  /content/projects/{id}        Update project
  DELETE /content/projects/{id}        Soft-delete project
  POST   /content/projects/{id}/generate  Generate AI variants
  GET    /content/projects/{id}/variants  List variants for project
  POST   /content/projects/{id}/schedule  Schedule for publishing
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, WorkspaceCtx
from app.domains.schemas import ContentProjectCreate, ContentProjectResponse, ContentVariantResponse

router = APIRouter(prefix="/content/projects", tags=["content"])


@router.get("", response_model=list[ContentProjectResponse])
async def list_projects(
    workspace: CurrentWorkspace,
    db: DbSession,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List content projects for the workspace."""
    from app.repositories.repositories import ContentProjectRepository

    repo = ContentProjectRepository(db, workspace.id)
    return await repo.list_by_status(status=status, limit=limit, offset=offset)


@router.post("", response_model=ContentProjectResponse, status_code=201)
async def create_project(
    body: ContentProjectCreate,
    workspace: CurrentWorkspace,
    user: CurrentUser,
    db: DbSession,
):
    """Create a new content project."""
    from app.domains.execution.models import ContentProject, ProjectStatus

    project = ContentProject(
        workspace_id=workspace.id,
        title=body.title,
        description=body.description,
        content_type=body.content_type,
        status=ProjectStatus.IDEA,
        niche_id=body.niche_id,
        content_pillars=body.content_pillars,
        mood=body.mood,
        target_platforms=body.target_platforms,
        source_insight_id=body.source_insight_id,
        source_trend_id=body.source_trend_id,
        created_by=user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ContentProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Get project details."""
    from app.repositories.repositories import ContentProjectRepository

    repo = ContentProjectRepository(db, workspace.id)
    project = await repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ContentProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    mood: str | None = None,
    content_type: str | None = None,
):
    """Update a content project."""
    from app.domains.execution.models import ContentProject, ProjectStatus

    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if status is not None:
        try:
            update_data["status"] = ProjectStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if mood is not None:
        update_data["mood"] = mood
    if content_type is not None:
        update_data["content_type"] = content_type

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.execute(
        update(ContentProject)
        .where(
            ContentProject.id == project_id,
            ContentProject.workspace_id == workspace.id,
            ContentProject.deleted_at.is_(None),
        )
        .values(**update_data)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.repositories.repositories import ContentProjectRepository
    repo = ContentProjectRepository(db, workspace.id)
    return await repo.get_by_id(project_id)


@router.delete("/{project_id}", status_code=204, response_model=None)
async def delete_project(
    project_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """Soft-delete a content project."""
    from app.domains.execution.models import ContentProject

    result = await db.execute(
        update(ContentProject)
        .where(
            ContentProject.id == project_id,
            ContentProject.workspace_id == workspace.id,
        )
        .values(deleted_at=datetime.now(timezone.utc))
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/generate", status_code=202)
async def generate_variants(
    project_id: uuid.UUID,
    workspace: CurrentWorkspace,
    user: CurrentUser,
    db: DbSession,
    platforms: list[str] | None = None,
):
    """Generate AI content variants for a project.

    This uses the unified LLM provider to generate platform-specific content.
    Default platforms: twitter, linkedin, instagram, youtube.
    """
    from app.domains.execution.models import (
        ContentProject, ContentVariant, AuthoringSource, ProjectStatus,
    )
    from app.integrations.llm.provider import create_llm_provider, TaskType
    from app.config import get_settings

    # Load project
    project = await db.execute(
        select(ContentProject).where(
            ContentProject.id == project_id,
            ContentProject.workspace_id == workspace.id,
            ContentProject.deleted_at.is_(None),
        )
    )
    project = project.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_platforms = platforms or project.target_platforms or [
        "twitter", "linkedin", "instagram", "youtube",
    ]

    settings = get_settings()
    llm = create_llm_provider(
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GEMINI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
    )

    variants_created = []

    for platform in target_platforms:
        prompt = _build_generation_prompt(project, platform)
        try:
            response = await llm.complete(
                task_type=TaskType.GENERATION,
                messages=[
                    {"role": "system", "content": "You are a world-class social media content creator. Generate engaging, platform-optimized content."},
                    {"role": "user", "content": prompt},
                ],
                workspace_id=workspace.id,
                json_mode=True,
            )

            import json
            try:
                content_data = json.loads(response.content)
            except json.JSONDecodeError:
                content_data = {"caption": response.content}

            variant = ContentVariant(
                workspace_id=workspace.id,
                project_id=project.id,
                target_platform=platform,
                hook=content_data.get("hook", ""),
                caption=content_data.get("caption", ""),
                hashtags=content_data.get("hashtags", []),
                call_to_action=content_data.get("call_to_action", ""),
                script_outline=content_data.get("script_outline", ""),
                thread_tweets=content_data.get("thread_tweets", []),
                engagement_tips=content_data.get("engagement_tips", []),
                authoring_source=AuthoringSource.ASSISTANT,
                prompt_version="v2.0",
                provider_metadata={
                    "provider": response.provider,
                    "model": response.model,
                    "tokens_in": response.tokens_in,
                    "tokens_out": response.tokens_out,
                    "cost_usd": response.cost_usd,
                },
            )
            db.add(variant)
            variants_created.append(platform)

        except Exception as exc:
            import structlog
            structlog.get_logger().warning(
                "variant_generation_failed",
                platform=platform,
                project_id=str(project_id),
                error=str(exc),
            )

    # Move project to draft if it was an idea
    if project.status.value == "idea" and variants_created:
        await db.execute(
            update(ContentProject)
            .where(ContentProject.id == project.id)
            .values(status=ProjectStatus.DRAFT)
        )

    await db.flush()

    return {
        "status": "ok",
        "variants_created": variants_created,
        "total": len(variants_created),
    }


@router.get("/{project_id}/variants", response_model=list[ContentVariantResponse])
async def list_variants(
    project_id: uuid.UUID,
    workspace: CurrentWorkspace,
    db: DbSession,
):
    """List all content variants for a project."""
    from app.domains.execution.models import ContentVariant

    result = await db.execute(
        select(ContentVariant).where(
            ContentVariant.project_id == project_id,
            ContentVariant.workspace_id == workspace.id,
        )
        .order_by(ContentVariant.created_at.desc())
    )
    return result.scalars().all()


def _build_generation_prompt(project, platform: str) -> str:
    """Build a platform-specific content generation prompt."""
    platform_guides = {
        "twitter": "Create a Twitter/X thread (3-5 tweets). First tweet is the hook. Include relevant hashtags. Keep each tweet under 280 characters.",
        "linkedin": "Create a LinkedIn post. Professional tone. Start with a strong hook. Use line breaks for readability. Include 3-5 relevant hashtags.",
        "instagram": "Create an Instagram caption. Start with an attention-grabbing hook. Use emojis strategically. Include 15-20 relevant hashtags. Add a clear CTA.",
        "youtube": "Create a YouTube video script outline with: title, hook (first 5 seconds), key points, CTA, and suggested tags.",
        "tiktok": "Create a TikTok script. Hook in first 2 seconds. Keep it under 60 seconds. Include trending sounds/format suggestions.",
    }

    guide = platform_guides.get(platform, f"Create content optimized for {platform}.")
    mood_text = f"Mood/tone: {project.mood}" if project.mood else "Mood: engaging and authentic"
    pillars_text = f"Content pillars: {', '.join(project.content_pillars)}" if project.content_pillars else ""

    return f"""Generate social media content for the following project:

Title: {project.title}
Description: {project.description or 'No description provided'}
{mood_text}
{pillars_text}
Platform: {platform}

{guide}

Return JSON with these fields:
- hook: string (attention-grabbing opening)
- caption: string (main content body)
- hashtags: list of strings
- call_to_action: string
- script_outline: string (for video platforms)
- thread_tweets: list of strings (for Twitter)
- engagement_tips: list of strings (tips for maximizing engagement)
"""
