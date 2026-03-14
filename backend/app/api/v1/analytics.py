"""Analytics routes."""
from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import CurrentUser, DbSession
from app.models.models import PostStatus
from app.repositories.repositories import PostRepository
from app.schemas.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(current_user: CurrentUser, db: DbSession) -> AnalyticsSummary:
    repo = PostRepository(db)
    posts = await repo.get_platform_stats(current_user.id)

    platform_counts: dict[str, int] = {}
    platform_success: dict[str, int] = {}

    for post in posts:
        for platform, status in (post.platform_status or {}).items():
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            if status == "published":
                platform_success[platform] = platform_success.get(platform, 0) + 1

    success_rates = {
        p: round(platform_success.get(p, 0) / count * 100, 1)
        for p, count in platform_counts.items()
    }

    return AnalyticsSummary(
        total_posts=len(posts),
        published_posts=sum(1 for p in posts if p.status == PostStatus.PUBLISHED),
        partial_posts=sum(1 for p in posts if p.status == PostStatus.PARTIAL),
        failed_posts=sum(1 for p in posts if p.status == PostStatus.FAILED),
        platform_distribution=platform_counts,
        platform_success_rate=success_rates,
    )
