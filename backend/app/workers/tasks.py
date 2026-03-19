"""Celery tasks — post distribution + content agent pipeline."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime, timezone
import httpx, structlog
from app.workers.celery_app import celery_app
from app.constants import CELERY_MAX_RETRIES, CELERY_RETRY_BACKOFF_S

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.run_content_agent",
    bind=True,
    max_retries=2,
    soft_time_limit=1800,   # 30 min soft limit — creative pass can be slow
    time_limit=2100,        # 35 min hard kill
)
def run_content_agent(self, triggered_by: str = "celery_beat") -> dict:
    """Multi-agent orchestrated pipeline: Scout→Score→Analyst→FactCheck→Creative.

    Runs every 2 h via beat.  Can also be triggered manually via
    POST /api/v1/agent/run-collection which passes triggered_by="manual_api".
    """
    try:
        return asyncio.run(
            _run_orchestrated_pipeline(triggered_by=triggered_by)
        )
    except Exception as exc:
        logger.error("run_content_agent_task_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _run_orchestrated_pipeline(triggered_by: str = "celery_beat") -> dict:
    from app.config import get_settings
    from app.services.content_agent.orchestrator import run_orchestrated_pipeline

    settings = get_settings()
    return await run_orchestrated_pipeline(
        triggered_by=triggered_by,
        anthropic_key=getattr(settings, "ANTHROPIC_API_KEY", ""),
        gemini_key=getattr(settings, "GEMINI_API_KEY", ""),
        openai_key=getattr(settings, "OPENAI_API_KEY", ""),
        youtube_api_key=getattr(settings, "YOUTUBE_API_KEY", ""),
    )


@celery_app.task(bind=True, name="app.workers.tasks.distribute_post",
    max_retries=CELERY_MAX_RETRIES, default_retry_delay=CELERY_RETRY_BACKOFF_S, acks_late=True)
def distribute_post(self, post_id: str) -> dict:
    return asyncio.run(_distribute(self, post_id))


async def _distribute(task, post_id: str) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.models.models import Post, PostStatus, User
    from app.repositories.repositories import PostRepository, UserRepository
    from app.services.auth_service import AuthService
    from app.services.cache_service import get_cache_instance
    from app.config import get_settings
    from sqlalchemy import select as sa_select
    settings = get_settings()
    cache = get_cache_instance()
    async with AsyncSessionLocal() as db:
        await db.begin()
        try:
            post_repo = PostRepository(db)
            post = await post_repo.get_by_id(uuid.UUID(post_id))
            if not post:
                return {"error": "post_not_found"}
            result = await db.execute(sa_select(User).where(User.id == post.user_id))
            user = result.scalar_one_or_none()
            if not user:
                return {"error": "user_not_found"}
            post.status = PostStatus.PROCESSING
            await db.flush()
            auth_svc = AuthService(UserRepository(db), cache)
            platform_status = dict(post.platform_status or {})
            results: dict[str, str] = {}
            for platform in post.target_platforms:
                if platform_status.get(platform) == "published":
                    results[platform] = "published"; continue
                token_data = auth_svc.get_platform_token(user, platform)
                if not token_data:
                    results[platform] = "failed:not_connected"; continue
                content = (post.platform_content or {}).get(platform, {})
                caption = content.get("full_text") or post.caption or ""
                try:
                    await _publish_to_platform(platform, token_data, post, caption, settings)
                    results[platform] = "published"
                except Exception as exc:
                    results[platform] = f"failed:{type(exc).__name__}"
            post.platform_status = {**platform_status, **results}
            success = sum(1 for s in results.values() if s == "published")
            failed = sum(1 for s in results.values() if s.startswith("failed"))
            if success > 0 and failed == 0:
                post.status = PostStatus.PUBLISHED
                post.published_at = datetime.now(timezone.utc)
            elif success > 0:
                post.status = PostStatus.PARTIAL
            else:
                post.status = PostStatus.FAILED
            await db.commit()
            await _notify_user(cache, str(post.user_id), success, failed)
            return {"success": success, "failed": failed}
        except Exception as exc:
            await db.rollback()
            raise task.retry(exc=exc)


async def _publish_to_platform(platform, token, post, caption, settings):
    from app.services.platforms import InstagramService, YouTubeService, FacebookService, LinkedInService, TwitterService
    if platform == "instagram":
        svc = InstagramService(token["access_token"], token["user_id"])
        if post.media_type == "image": await svc.post_image(post.media_url, caption)
        elif post.media_type == "video": await svc.post_reel(post.media_url, caption)
    elif platform in ("youtube", "youtube_shorts"):
        svc = YouTubeService(token["access_token"])
        async with httpx.AsyncClient(timeout=120.0) as client:
            video_bytes = (await client.get(post.media_url)).content
        await svc.upload_video(video_bytes, post.title or "New Video", caption, is_short=(platform=="youtube_shorts"))
    elif platform == "facebook":
        svc = FacebookService(token["access_token"], token["page_id"])
        if post.media_type == "text": await svc.post_text(caption)
        elif post.media_type == "image": await svc.post_photo(post.media_url, caption)
        elif post.media_type == "video": await svc.post_video(post.media_url, caption, post.title or "")
    elif platform == "linkedin":
        svc = LinkedInService(token["access_token"], token["person_urn"])
        if post.media_type == "text": await svc.post_text(caption)
        else: await svc.post_image(post.media_url, caption)
    elif platform == "x":
        svc = TwitterService(token["api_key"], token["api_secret"], token["access_token"], token["access_secret"])
        await svc.post_tweet(caption)


async def _notify_user(cache, user_id, success, failed):
    sub = await cache.get_push_subscription(user_id)
    if not sub: return
    try:
        from pywebpush import webpush
        from app.config import get_settings
        import json
        s = get_settings()
        if not s.VAPID_PRIVATE_KEY: return
        title = "✅ Published!" if failed == 0 else "⚠️ Partial publish"
        body = f"Posted to {success} platform(s)" if failed == 0 else f"{success} succeeded, {failed} failed"
        webpush(subscription_info=sub, data=json.dumps({"title": title, "body": body}),
            vapid_private_key=s.VAPID_PRIVATE_KEY, vapid_claims={"sub": f"mailto:{s.VAPID_EMAIL}"})
    except Exception as exc:
        logger.warning("push_failed", user_id=user_id, error=str(exc))