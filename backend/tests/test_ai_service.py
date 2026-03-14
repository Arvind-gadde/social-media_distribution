"""Unit tests for AIService — no external calls."""
import pytest
from app.services.ai_service import AIService


@pytest.fixture
def ai():
    return AIService(openai_api_key=None)


class TestRecommendations:
    def test_short_video_recommends_instagram(self, ai):
        recs = ai.recommend_platforms("video", 20)
        platforms = [r["platform"] for r in recs]
        assert "instagram" in platforms

    def test_long_video_recommends_youtube(self, ai):
        recs = ai.recommend_platforms("video", 600)
        assert recs[0]["platform"] == "youtube"

    def test_regional_language_adds_sharechat(self, ai):
        recs = ai.recommend_platforms("image", 0, "hi")
        assert any(r["platform"] == "sharechat" for r in recs)

    def test_scores_between_zero_and_one(self, ai):
        recs = ai.recommend_platforms("text", 0, "en")
        assert all(0 < r["score"] <= 1 for r in recs)

    def test_recs_sorted_descending(self, ai):
        recs = ai.recommend_platforms("video", 45)
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_unknown_media_type_returns_text_recs(self, ai):
        recs = ai.recommend_platforms("unknown", 0)
        assert len(recs) > 0


class TestCaptionBuilding:
    def test_trims_to_platform_limit(self, ai):
        long_caption = "x" * 1000
        result = ai.build_platform_caption(long_caption, "x")
        assert len(result["caption"]) <= 280

    def test_instagram_caption_not_trimmed_if_short(self, ai):
        caption = "Hello world"
        result = ai.build_platform_caption(caption, "instagram")
        assert result["caption"] == caption

    def test_includes_hashtags(self, ai):
        result = ai.build_platform_caption("test", "instagram")
        assert len(result["hashtags"]) > 0

    def test_full_text_combines_caption_and_hashtags(self, ai):
        result = ai.build_platform_caption("test caption", "josh")
        assert "test caption" in result["full_text"]
        assert "#Josh" in result["full_text"]

    def test_linkedin_has_no_default_hashtags(self, ai):
        result = ai.build_platform_caption("test", "linkedin")
        assert result["hashtags"] == []


class TestAICaptionErrors:
    @pytest.mark.asyncio
    async def test_raises_when_no_openai_key(self, ai):
        from app.exceptions import AIServiceError
        with pytest.raises(AIServiceError, match="OpenAI API key"):
            await ai.generate_ai_caption("topic", "casual", "en", "video", [])

    @pytest.mark.asyncio
    async def test_raises_on_unsupported_tone(self, ai):
        from app.exceptions import AIServiceError
        ai_with_key = AIService(openai_api_key="fake")
        with pytest.raises(AIServiceError, match="Unsupported tone"):
            await ai_with_key.generate_ai_caption("topic", "angry", "en", "video", [])
