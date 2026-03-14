"""Unit tests for PostService — uses in-memory mocks."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.models import Post, PostStatus
from app.services.post_service import PostService


@pytest.fixture
def mock_post_repo():
    repo = AsyncMock()
    repo.save = AsyncMock(side_effect=lambda p: p)
    repo.get_by_id = AsyncMock()
    repo.delete_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_ai():
    ai = MagicMock()
    ai.recommend_platforms.return_value = [
        {"platform": "instagram", "reason": "best", "score": 0.95}
    ]
    ai.build_platform_caption.return_value = {
        "caption": "test", "hashtags": [], "full_text": "test"
    }
    return ai


@pytest.fixture
def service(mock_post_repo, mock_ai):
    return PostService(mock_post_repo, mock_ai)


class TestCreateDraft:
    @pytest.mark.asyncio
    async def test_creates_post_with_correct_fields(self, service, mock_post_repo):
        user_id = uuid.uuid4()
        post = await service.create_draft(
            user_id, caption="hello", target_platforms=["instagram"],
            media_key=None, media_url=None, media_type="text", media_duration_s=None,
        )
        assert post.user_id == user_id
        assert post.caption == "hello"
        assert post.target_platforms == ["instagram"]
        assert post.status == PostStatus.DRAFT

    @pytest.mark.asyncio
    async def test_scheduled_post_has_scheduled_status(self, service):
        from datetime import datetime, timezone
        user_id = uuid.uuid4()
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        post = await service.create_draft(
            user_id, caption="test", target_platforms=["x"],
            media_key=None, media_url=None, media_type="text",
            media_duration_s=None, scheduled_at=future,
        )
        assert post.status == PostStatus.SCHEDULED


class TestFinalize:
    @pytest.mark.asyncio
    async def test_all_success_sets_published(self, service, mock_post_repo):
        post = Post(
            id=uuid.uuid4(), user_id=uuid.uuid4(),
            platform_status={"instagram": "published", "facebook": "published"},
            target_platforms=["instagram", "facebook"],
        )
        mock_post_repo.get_by_id.return_value = post
        result = await service.finalize(post.id)
        assert result.status == PostStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_mixed_results_sets_partial(self, service, mock_post_repo):
        post = Post(
            id=uuid.uuid4(), user_id=uuid.uuid4(),
            platform_status={"instagram": "published", "youtube": "failed:error"},
            target_platforms=["instagram", "youtube"],
        )
        mock_post_repo.get_by_id.return_value = post
        result = await service.finalize(post.id)
        assert result.status == PostStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_all_failed_sets_failed(self, service, mock_post_repo):
        post = Post(
            id=uuid.uuid4(), user_id=uuid.uuid4(),
            platform_status={"instagram": "failed:timeout"},
            target_platforms=["instagram"],
        )
        mock_post_repo.get_by_id.return_value = post
        result = await service.finalize(post.id)
        assert result.status == PostStatus.FAILED
