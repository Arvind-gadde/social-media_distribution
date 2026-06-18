"""Tests for Predictive Virality Agent and Virality Predictor service."""
import pytest
from datetime import datetime, timezone
from app.services.virality.virality_predictor import ViralityPredictor


class TestViralityPredictor:
    """Test the ViralityPredictor service."""
    
    def test_init(self):
        """Test predictor initialization."""
        predictor = ViralityPredictor()
        assert predictor is not None
        assert len(predictor.SIGNAL_WEIGHTS) == 12
        assert sum(predictor.SIGNAL_WEIGHTS.values()) == pytest.approx(1.0, 0.01)
    
    def test_predict_virality_basic(self):
        """Test basic virality prediction."""
        predictor = ViralityPredictor()
        
        content = {
            "title": "5 Amazing Tips for Content Creators",
            "caption": "Save this for later! What's your favorite tip? Comment below!",
            "hashtags": ["#contentcreator", "#tips", "#socialmedia"],
            "content_type": "reel",
            "scheduled_at": "2024-01-15T18:00:00Z",
            "has_thumbnail": True,
            "media_count": 1,
            "has_audio": True,
        }
        
        result = predictor.predict_virality(
            content=content,
            platform="instagram",
        )
        
        assert "overall_score" in result
        assert "grade" in result
        assert "signals" in result
        assert "top_strengths" in result
        assert "top_weaknesses" in result
        assert "improvements" in result
        assert "predicted_range" in result
        assert "confidence" in result
        
        assert 0 <= result["overall_score"] <= 1
        assert len(result["signals"]) == 12
        assert len(result["top_strengths"]) == 3
        assert len(result["top_weaknesses"]) == 3
    
    def test_score_hook_strength(self):
        """Test hook strength scoring."""
        predictor = ViralityPredictor()
        
        # Strong hook with number
        strong_score = predictor.score_hook_strength(
            "5 secrets nobody tells you about content creation",
            ""
        )
        assert strong_score > 0.7
        
        # Weak hook
        weak_score = predictor.score_hook_strength(
            "My content today",
            ""
        )
        assert weak_score < 0.7
        
        # Empty hook
        empty_score = predictor.score_hook_strength("", "")
        assert empty_score == 0.3
    
    def test_score_emotional_resonance(self):
        """Test emotional resonance scoring."""
        predictor = ViralityPredictor()
        
        # High emotional content
        high_score = predictor.score_emotional_resonance(
            "This is amazing! The secret nobody tells you. You won't believe this!"
        )
        assert high_score > 0.6
        
        # Low emotional content
        low_score = predictor.score_emotional_resonance(
            "Here is some content."
        )
        assert low_score < 0.6
    
    def test_score_shareability(self):
        """Test shareability scoring."""
        predictor = ViralityPredictor()
        
        # High shareability
        high_score = predictor.score_shareability(
            "Tag someone who needs to see this! Share with your friends!",
            "tutorial"
        )
        assert high_score > 0.7
        
        # Low shareability
        low_score = predictor.score_shareability(
            "Just posting this.",
            "post"
        )
        assert low_score < 0.6
    
    def test_score_trend_alignment(self):
        """Test trend alignment scoring."""
        predictor = ViralityPredictor()
        
        trending_topics = ["AI", "content creation", "viral"]
        
        # High alignment
        high_score = predictor.score_trend_alignment(
            ["#AI", "#contentcreation"],
            "Learn about AI and content creation",
            trending_topics
        )
        assert high_score > 0.6
        
        # Low alignment
        low_score = predictor.score_trend_alignment(
            ["#random"],
            "Random content",
            trending_topics
        )
        assert low_score < 0.6
    
    def test_score_caption_engagement(self):
        """Test caption engagement scoring."""
        predictor = ViralityPredictor()
        
        # High engagement caption
        high_score = predictor.score_caption_engagement(
            "What do you think? Comment your thoughts below! 🔥 Let me know your opinion!"
        )
        assert high_score > 0.6
        
        # Low engagement caption
        low_score = predictor.score_caption_engagement(
            "Post"
        )
        assert low_score < 0.6
    
    def test_score_hashtag_reach(self):
        """Test hashtag reach scoring."""
        predictor = ViralityPredictor()
        
        # Optimal hashtag count for Instagram
        optimal_score = predictor.score_hashtag_reach(
            ["#tag" + str(i) for i in range(15)],
            "instagram"
        )
        assert optimal_score > 0.6
        
        # Too few hashtags
        few_score = predictor.score_hashtag_reach(
            ["#tag1"],
            "instagram"
        )
        assert few_score < optimal_score
        
        # No hashtags
        none_score = predictor.score_hashtag_reach([], "instagram")
        assert none_score == 0.3
    
    def test_score_platform_fit(self):
        """Test platform fit scoring."""
        predictor = ViralityPredictor()
        
        # Perfect fit
        perfect_score = predictor.score_platform_fit("reel", "instagram")
        assert perfect_score >= 0.9
        
        # Good fit
        good_score = predictor.score_platform_fit("post", "instagram")
        assert 0.7 <= good_score < 0.9
        
        # Unknown fit
        unknown_score = predictor.score_platform_fit("unknown", "unknown")
        assert unknown_score == 0.6
    
    def test_score_posting_time(self):
        """Test posting time scoring."""
        predictor = ViralityPredictor()
        
        # Optimal time for Instagram (6 PM)
        optimal_score = predictor.score_posting_time(
            "2024-01-15T18:00:00Z",
            "instagram"
        )
        assert optimal_score > 0.7
        
        # Suboptimal time (3 AM)
        suboptimal_score = predictor.score_posting_time(
            "2024-01-15T03:00:00Z",
            "instagram"
        )
        assert suboptimal_score < optimal_score
        
        # No schedule
        none_score = predictor.score_posting_time(None, "instagram")
        assert none_score == 0.5
    
    def test_score_cta_strength(self):
        """Test CTA strength scoring."""
        predictor = ViralityPredictor()
        
        # Strong CTA
        strong_score = predictor.score_cta_strength(
            "Save this now! Share with friends! Comment below!"
        )
        assert strong_score > 0.7
        
        # Weak CTA
        weak_score = predictor.score_cta_strength(
            "Here's my content."
        )
        assert weak_score < 0.6
    
    def test_grade_conversion(self):
        """Test score to grade conversion."""
        predictor = ViralityPredictor()
        
        assert predictor._get_grade(0.95) == "A+"
        assert predictor._get_grade(0.85) == "A"
        assert predictor._get_grade(0.75) == "B+"
        assert predictor._get_grade(0.65) == "B-"
        assert predictor._get_grade(0.55) == "C"
        assert predictor._get_grade(0.45) == "D"
    
    def test_predict_with_historical_data(self):
        """Test prediction with historical performance data."""
        predictor = ViralityPredictor()
        
        content = {
            "title": "Great content",
            "caption": "Check this out!",
            "hashtags": ["#test"],
            "content_type": "post",
        }
        
        historical_performance = {
            "past_titles": ["Old content", "Previous post"],
            "avg_views": 5000,
            "avg_engagement_rate": 0.08,
        }
        
        result = predictor.predict_virality(
            content=content,
            platform="instagram",
            historical_performance=historical_performance,
        )
        
        # Check that historical data influenced predictions
        assert result["predicted_range"]["views_likely"] > 1000  # Should use historical data
        assert result["confidence"] in ["low", "medium", "high"]
    
    def test_improvements_generated(self):
        """Test that improvements are generated for weak signals."""
        predictor = ViralityPredictor()
        
        # Content with obvious weaknesses
        weak_content = {
            "title": "Post",
            "caption": "Content",
            "hashtags": [],
            "content_type": "post",
        }
        
        result = predictor.predict_virality(
            content=weak_content,
            platform="instagram",
        )
        
        assert len(result["improvements"]) > 0
        assert any("hashtag" in imp.lower() for imp in result["improvements"])


# Agent integration tests would go here
# These require database fixtures and are similar to other agent tests
