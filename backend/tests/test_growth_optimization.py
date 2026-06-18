"""Tests for Growth Optimization Agent and Growth Optimizer service."""
import pytest
from datetime import datetime, timezone
from app.services.growth.growth_optimizer import GrowthOptimizer


class TestGrowthOptimizer:
    """Test the GrowthOptimizer service."""
    
    def test_init(self):
        """Test optimizer initialization."""
        optimizer = GrowthOptimizer()
        assert optimizer is not None
        assert len(optimizer.HASHTAG_LIMITS) > 0
        assert len(optimizer.CTA_BENCHMARKS) > 0
    
    def test_analyze_hashtag_performance_empty(self):
        """Test hashtag analysis with no data."""
        optimizer = GrowthOptimizer()
        result = optimizer.analyze_hashtag_performance([])
        
        assert result["total_hashtags_analyzed"] == 0
        assert result["top_performing_hashtags"] == []
        assert "recommendations" in result  # May be empty or have generic advice
    
    def test_analyze_hashtag_performance_with_data(self):
        """Test hashtag analysis with content data."""
        optimizer = GrowthOptimizer()
        
        content_items = [
            {
                "hashtags": ["#tech", "#AI", "#coding"],
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
                "saves": 20,
            },
            {
                "hashtags": ["#tech", "#programming"],
                "views": 1500,
                "likes": 200,
                "comments": 20,
                "shares": 10,
                "saves": 30,
            },
            {
                "hashtags": ["#AI", "#machinelearning"],
                "views": 800,
                "likes": 80,
                "comments": 8,
                "shares": 4,
                "saves": 15,
            },
        ]
        
        result = optimizer.analyze_hashtag_performance(content_items)
        
        assert result["total_hashtags_analyzed"] > 0
        assert len(result["top_performing_hashtags"]) > 0
        assert len(result["recommendations"]) > 0
        
        # Check hashtag data structure
        for hashtag in result["top_performing_hashtags"]:
            assert "hashtag" in hashtag
            assert "usage_count" in hashtag
            assert "avg_engagement_rate" in hashtag
            assert "performance_score" in hashtag
    
    def test_optimize_hashtag_strategy(self):
        """Test hashtag strategy optimization."""
        optimizer = GrowthOptimizer()
        
        performance_data = {
            "top_performing_hashtags": [
                {"hashtag": "#tech", "avg_engagement_rate": 0.15},
                {"hashtag": "#AI", "avg_engagement_rate": 0.12},
            ]
        }
        
        result = optimizer.optimize_hashtag_strategy(
            platform="instagram",
            niche_keywords=["technology", "coding", "developer"],
            current_hashtags=["#tech", "#programming"],
            performance_data=performance_data,
        )
        
        assert result["platform"] == "instagram"
        assert result["recommended_count"] > 0
        assert result["max_allowed"] == 30  # Instagram limit
        assert len(result["recommended_hashtags"]) > 0
        assert "expected_impact" in result
        
        # Check hashtag structure
        for hashtag in result["recommended_hashtags"]:
            assert "hashtag" in hashtag
            assert "reason" in hashtag
            assert "category" in hashtag
    
    def test_analyze_comment_engagement_empty(self):
        """Test comment analysis with no data."""
        optimizer = GrowthOptimizer()
        result = optimizer.analyze_comment_engagement([])
        
        assert result["total_content_analyzed"] == 0
        assert result["avg_comments_per_post"] == 0
        assert result["comment_rate"] == 0
    
    def test_analyze_comment_engagement_with_data(self):
        """Test comment analysis with content data."""
        optimizer = GrowthOptimizer()
        
        content_items = [
            {
                "comments": 50,
                "views": 1000,
                "caption": "What do you think? Comment below!",
            },
            {
                "comments": 30,
                "views": 800,
                "caption": "Do you agree or disagree?",
            },
            {
                "comments": 20,
                "views": 600,
                "caption": "Let me know your thoughts!",
            },
        ]
        
        result = optimizer.analyze_comment_engagement(content_items)
        
        assert result["total_content_analyzed"] == 3
        assert result["total_comments"] == 100
        assert result["avg_comments_per_post"] > 0
        assert result["comment_rate"] > 0
        assert len(result["best_comment_triggers"]) > 0
        assert len(result["recommendations"]) > 0
    
    def test_analyze_cta_effectiveness_empty(self):
        """Test CTA analysis with no data."""
        optimizer = GrowthOptimizer()
        result = optimizer.analyze_cta_effectiveness([])
        
        assert result["ctas_analyzed"] == 0
        assert "recommendations" in result  # May be empty or have generic advice
    
    def test_analyze_cta_effectiveness_with_data(self):
        """Test CTA analysis with content data."""
        optimizer = GrowthOptimizer()
        
        content_items = [
            {
                "caption": "Follow for more tech tips!",
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
                "saves": 20,
            },
            {
                "caption": "Save this for later!",
                "views": 1500,
                "likes": 150,
                "comments": 15,
                "shares": 8,
                "saves": 50,
            },
            {
                "caption": "Comment your favorite tool below!",
                "views": 800,
                "likes": 80,
                "comments": 30,
                "shares": 4,
                "saves": 15,
            },
        ]
        
        result = optimizer.analyze_cta_effectiveness(content_items)
        
        assert result["ctas_analyzed"] > 0
        assert len(result["cta_performance"]) > 0
        assert result["top_performing_cta"] is not None
        assert len(result["recommendations"]) > 0
        
        # Check CTA performance structure
        for cta, stats in result["cta_performance"].items():
            assert "usage_count" in stats
            assert "avg_engagement_rate" in stats
            assert "performance" in stats
    
    def test_detect_viral_loops_empty(self):
        """Test viral loop detection with no data."""
        optimizer = GrowthOptimizer()
        result = optimizer.detect_viral_loops([])
        
        assert result["viral_content_count"] == 0
        assert "recommendations" in result  # May be empty or have generic advice
    
    def test_detect_viral_loops_with_data(self):
        """Test viral loop detection with content data."""
        optimizer = GrowthOptimizer()
        
        content_items = [
            {
                "title": "Viral Post 1",
                "views": 1000,
                "likes": 150,
                "comments": 20,
                "shares": 30,
                "saves": 40,
                "hashtags": ["#viral", "#trending"],
                "content_type": "short_video",
            },
            {
                "title": "Normal Post",
                "views": 500,
                "likes": 25,
                "comments": 5,
                "shares": 2,
                "saves": 3,
                "hashtags": ["#tech"],
                "content_type": "post",
            },
            {
                "title": "Viral Post 2",
                "views": 2000,
                "likes": 300,
                "comments": 40,
                "shares": 50,
                "saves": 60,
                "hashtags": ["#viral", "#AI"],
                "content_type": "short_video",
            },
        ]
        
        result = optimizer.detect_viral_loops(content_items)
        
        assert result["viral_content_count"] > 0
        assert result["viral_rate"] > 0
        assert result["viral_threshold"] == 0.10
        assert len(result["viral_content"]) > 0
        assert len(result["viral_patterns"]) > 0
        assert len(result["recommendations"]) > 0
    
    def test_calculate_growth_score(self):
        """Test overall growth score calculation."""
        optimizer = GrowthOptimizer()
        
        hashtag_performance = {
            "top_performing_hashtags": [
                {"avg_engagement_rate": 0.10}
            ]
        }
        
        comment_engagement = {
            "comment_rate": 0.03
        }
        
        cta_effectiveness = {
            "cta_performance": {
                "save": {"avg_engagement_rate": 0.08},
                "comment": {"avg_engagement_rate": 0.05},
            }
        }
        
        viral_loops = {
            "viral_rate": 0.15
        }
        
        result = optimizer.calculate_growth_score(
            hashtag_performance,
            comment_engagement,
            cta_effectiveness,
            viral_loops,
        )
        
        assert "overall_score" in result
        assert "score_breakdown" in result
        assert "grade" in result
        assert "top_strength" in result
        assert "top_weakness" in result
        
        assert 0 <= result["overall_score"] <= 100
        assert result["grade"] in ["A", "B", "C", "D", "F"]
        
        # Check score breakdown
        breakdown = result["score_breakdown"]
        assert "hashtag_strategy" in breakdown
        assert "comment_engagement" in breakdown
        assert "cta_effectiveness" in breakdown
        assert "viral_potential" in breakdown
    
    def test_hashtag_limits_defined(self):
        """Test that hashtag limits are defined for all platforms."""
        optimizer = GrowthOptimizer()
        
        expected_platforms = ["instagram", "tiktok", "twitter", "linkedin", "youtube", "facebook"]
        for platform in expected_platforms:
            assert platform in optimizer.HASHTAG_LIMITS
            assert optimizer.HASHTAG_LIMITS[platform] > 0
    
    def test_cta_benchmarks_defined(self):
        """Test that CTA benchmarks are defined."""
        optimizer = GrowthOptimizer()
        
        expected_ctas = ["follow", "like", "comment", "share", "save", "click_link", "dm"]
        for cta in expected_ctas:
            assert cta in optimizer.CTA_BENCHMARKS
            benchmark = optimizer.CTA_BENCHMARKS[cta]
            assert "baseline" in benchmark
            assert "good" in benchmark
            assert "excellent" in benchmark
            assert benchmark["baseline"] < benchmark["good"] < benchmark["excellent"]
    
    def test_hashtag_categories_defined(self):
        """Test that hashtag categories are defined."""
        optimizer = GrowthOptimizer()
        
        expected_categories = ["niche", "small", "medium", "large", "mega"]
        for category in expected_categories:
            assert category in optimizer.HASHTAG_CATEGORIES
            min_val, max_val = optimizer.HASHTAG_CATEGORIES[category]
            assert min_val < max_val or max_val == float('inf')
    
    def test_grade_conversion(self):
        """Test score to grade conversion."""
        optimizer = GrowthOptimizer()
        
        assert optimizer._get_grade(95) == "A"
        assert optimizer._get_grade(85) == "B"
        assert optimizer._get_grade(75) == "C"
        assert optimizer._get_grade(65) == "D"
        assert optimizer._get_grade(50) == "F"
    
    def test_hashtag_normalization(self):
        """Test that hashtags are normalized correctly."""
        optimizer = GrowthOptimizer()
        
        content_items = [
            {
                "hashtags": ["#Tech", "#TECH", "tech"],  # Different cases
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
                "saves": 20,
            },
        ]
        
        result = optimizer.analyze_hashtag_performance(content_items)
        
        # All variations should be counted as one hashtag
        assert result["total_hashtags_analyzed"] == 1
        
        # The normalized hashtag should appear in results
        hashtag_found = False
        for hashtag in result["top_performing_hashtags"]:
            if "tech" in hashtag["hashtag"].lower():
                hashtag_found = True
                assert hashtag["usage_count"] == 3  # All 3 variations counted
        
        assert hashtag_found


# Agent integration tests would go here
# These require database fixtures and are similar to other agent tests
