"""Post service — business logic for creating and managing posts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from langdetect import detect as detect_language, LangDetectException

from app.constants import PLATFORM_DEFAULT_HASHTAGS
from app.exceptions import NotFoundError, AuthorizationError
from app.models.models import Post, PostStatus, User
from app.repositories.repositories import PostRepository
from app.services.ai_service import AIService

logger = structlog.get_logger(__name__)


class PostService:
    """Orchestrates post creation, updates, and status transitions."""

    def __init__(self, post_repo: PostRepository, ai_service: AIService) -> None:
        self._repo = post_repo
        self._ai = ai_service

    async def create_draft(
        self,
        user_id: uuid.UUID,
        *,
        caption: str,
        target_platforms: list[str],
        media_key: Optional[str],
        media_url: Optional[str],
        media_type: str,
        media_duration_s: Optional[float],
        title: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Post:
        # Detect language from caption
        detected_lang = "en"
        if caption:
            try:
                detected_lang = detect_language(caption)
            except LangDetectException:
                pass

        # Build per-platform content at creation time
        platform_content = {
            p: self._ai.build_platform_caption(caption, p)
            for p in target_platforms
        }

        # Get AI recommendations
        recommendations = self._ai.recommend_platforms(
            media_type, media_duration_s or 0, detected_lang
        )

        status = PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT

        post = Post(
            user_id=user_id,
            title=title,
            caption=caption,
            media_key=media_key,
            media_url=media_url,
            media_type=media_type,
            media_duration_s=media_duration_s,
            detected_language=detected_lang,
            target_platforms=target_platforms,
            platform_content=platform_content,
            recommended_platforms=[r["platform"] for r in recommendations[:5]],
            platform_status={p: "pending" for p in target_platforms},
            status=status,
            scheduled_at=scheduled_at,
        )
        return await self._repo.save(post)

    async def get_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> Post:
        post = await self._repo.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post", str(post_id))
        if post.user_id != user_id:
            raise AuthorizationError("You do not have access to this post")
        return post

    async def mark_processing(self, post_id: uuid.UUID) -> Post:
        post = await self._repo.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post", str(post_id))
        post.status = PostStatus.PROCESSING
        return await self._repo.save(post)

    async def update_platform_status(
        self,
        post_id: uuid.UUID,
        platform: str,
        status: str,
    ) -> Post:
        post = await self._repo.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post", str(post_id))
        platform_status = dict(post.platform_status or {})
        platform_status[platform] = status
        post.platform_status = platform_status
        return await self._repo.save(post)

    async def finalize(self, post_id: uuid.UUID) -> Post:
        """Compute final status from per-platform results."""
        post = await self._repo.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post", str(post_id))

        statuses = list((post.platform_status or {}).values())
        success_count = sum(1 for s in statuses if s == "published")
        fail_count = sum(1 for s in statuses if str(s).startswith("failed"))

        if success_count > 0 and fail_count == 0:
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.now(timezone.utc)
        elif success_count > 0 and fail_count > 0:
            post.status = PostStatus.PARTIAL
        else:
            post.status = PostStatus.FAILED

        return await self._repo.save(post)

    async def reset_failed_platforms(self, post: Post) -> Post:
        """For retry: reset only failed platforms back to pending."""
        failed = [
            p for p, s in (post.platform_status or {}).items()
            if str(s).startswith("failed")
        ]
        if not failed:
            return post
        post.target_platforms = failed
        updated_status = dict(post.platform_status or {})
        for p in failed:
            updated_status[p] = "pending"
        post.platform_status = updated_status
        post.status = PostStatus.DRAFT
        return await self._repo.save(post)

    async def delete_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        """Delete post and return the S3 key for media cleanup."""
        post = await self.get_post(post_id, user_id)
        media_key = post.media_key
        await self._repo.delete_by_id(post_id)
        logger.info("post_deleted", post_id=str(post_id), user_id=str(user_id))
        return media_key
