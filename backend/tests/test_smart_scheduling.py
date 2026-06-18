"""Tests for Smart Scheduling Agent and Schedule Optimizer service."""
import pytest
from datetime import datetime, timedelta, timezone
from app.services.scheduling.schedule_optimizer import ScheduleOptimizer


class TestScheduleOptimizer:
    """Test the ScheduleOptimizer service."""
    
    def test_init(self):
        """Test optimizer initialization."""
        optimizer = ScheduleOptimizer()
        assert optimizer is not None
        assert len(optimizer.PLATFORM_PEAK_TIMES) > 0
    
    def test_analyze_audience_activity_empty(self):
        """Test audience activity analysis with no data."""
        optimizer = ScheduleOptimizer()
        result = optimizer.analyze_audience_activity([])
        
        assert result["peak_hours"] == []
        assert result["peak_days"] == []
        assert result["activity_by_hour"] == {}
        assert result["activity_by_day"] == {}
    
    def test_analyze_audience_activity_with_data(self):
        """Test audience activity analysis with content data."""
        optimizer = ScheduleOptimizer()
        
        # Create mock content with different posting times
        content_history = [
            {
                "published_at": datetime(2024, 1, 15, 18, 0, tzinfo=timezone.utc),  # Monday 6 PM
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
            },
            {
                "published_at": datetime(2024, 1, 16, 19, 0, tzinfo=timezone.utc),  # Tuesday 7 PM
                "views": 1500,
                "likes": 200,
                "comments": 20,
                "shares": 10,
            },
            {
                "published_at": datetime(2024, 1, 17, 18, 0, tzinfo=timezone.utc),  # Wednesday 6 PM
                "views": 1200,
                "likes": 150,
                "comments": 15,
                "shares": 8,
            },
        ]
        
        result = optimizer.analyze_audience_activity(content_history)
        
        assert len(result["peak_hours"]) > 0
        assert len(result["peak_days"]) > 0
        assert result["total_content_analyzed"] == 3
        assert isinstance(result["activity_by_hour"], dict)
        assert isinstance(result["activity_by_day"], dict)
    
    def test_get_platform_optimal_times_instagram(self):
        """Test getting optimal times for Instagram."""
        optimizer = ScheduleOptimizer()
        result = optimizer.get_platform_optimal_times("instagram")
        
        assert result["platform"] == "instagram"
        assert len(result["best_days"]) > 0
        assert len(result["best_times"]) > 0
        assert result["timezone"] == "UTC"
    
    def test_get_platform_optimal_times_with_content_type(self):
        """Test getting optimal times with content type modifier."""
        optimizer = ScheduleOptimizer()
        result = optimizer.get_platform_optimal_times("instagram", content_type="educational")
        
        assert result["platform"] == "instagram"
        assert result["content_type"] == "educational"
        assert "modifiers" in result
        assert "reasoning" in result
    
    def test_get_platform_optimal_times_unknown_platform(self):
        """Test getting optimal times for unknown platform (should fallback)."""
        optimizer = ScheduleOptimizer()
        result = optimizer.get_platform_optimal_times("unknown_platform")
        
        assert result["platform"] == "unknown_platform"
        assert len(result["best_days"]) > 0  # Should have fallback data
        assert len(result["best_times"]) > 0
    
    def test_analyze_competitor_schedule_empty(self):
        """Test competitor schedule analysis with no data."""
        optimizer = ScheduleOptimizer()
        result = optimizer.analyze_competitor_schedule([])
        
        assert result["competitor_peak_hours"] == []
        assert result["competitor_peak_days"] == []
        assert result["avoid_times"] == []
    
    def test_analyze_competitor_schedule_with_data(self):
        """Test competitor schedule analysis with posts."""
        optimizer = ScheduleOptimizer()
        
        competitor_posts = [
            {"posted_at": datetime(2024, 1, 15, 18, 0, tzinfo=timezone.utc)},
            {"posted_at": datetime(2024, 1, 16, 18, 0, tzinfo=timezone.utc)},
            {"posted_at": datetime(2024, 1, 17, 19, 0, tzinfo=timezone.utc)},
            {"posted_at": datetime(2024, 1, 18, 18, 0, tzinfo=timezone.utc)},
        ]
        
        result = optimizer.analyze_competitor_schedule(competitor_posts)
        
        assert len(result["competitor_peak_hours"]) > 0
        assert len(result["competitor_peak_days"]) > 0
        assert len(result["avoid_times"]) > 0
        assert result["total_posts_analyzed"] == 4
    
    def test_calculate_optimal_schedule_with_audience_data(self):
        """Test calculating optimal schedule with audience data."""
        optimizer = ScheduleOptimizer()
        
        audience_activity = {
            "peak_hours": ["18:00", "19:00", "20:00"],
            "peak_days": ["monday", "tuesday", "wednesday"],
            "activity_by_hour": {18: 0.8, 19: 0.9, 20: 0.7},
            "activity_by_day": {"monday": 0.8, "tuesday": 0.9, "wednesday": 0.7},
        }
        
        result = optimizer.calculate_optimal_schedule(
            platform="instagram",
            audience_activity=audience_activity,
            timezone="UTC",
        )
        
        assert result["platform"] == "instagram"
        assert len(result["best_days"]) > 0
        assert len(result["best_times"]) > 0
        assert result["timezone"] == "UTC"
        assert "reasoning" in result
        assert "recommended_frequency" in result
    
    def test_calculate_optimal_schedule_without_audience_data(self):
        """Test calculating optimal schedule without audience data (platform defaults)."""
        optimizer = ScheduleOptimizer()
        
        audience_activity = {
            "peak_hours": [],
            "peak_days": [],
        }
        
        result = optimizer.calculate_optimal_schedule(
            platform="youtube",
            audience_activity=audience_activity,
            timezone="UTC",
        )
        
        assert result["platform"] == "youtube"
        assert len(result["best_days"]) > 0
        assert len(result["best_times"]) > 0
        assert "youtube" in result["reasoning"].lower()  # Should mention platform (case-insensitive)
    
    def test_calculate_optimal_schedule_avoiding_competitors(self):
        """Test calculating schedule while avoiding competitor times."""
        optimizer = ScheduleOptimizer()
        
        audience_activity = {
            "peak_hours": ["18:00", "19:00", "20:00"],
            "peak_days": ["monday", "tuesday", "wednesday"],
        }
        
        competitor_schedule = {
            "avoid_times": ["18:00", "19:00"],
        }
        
        result = optimizer.calculate_optimal_schedule(
            platform="instagram",
            audience_activity=audience_activity,
            competitor_schedule=competitor_schedule,
            timezone="UTC",
        )
        
        assert result["platform"] == "instagram"
        # Should have filtered out competitor times
        assert "18:00" not in result["best_times"] or "19:00" not in result["best_times"]
        assert "competitor" in result["reasoning"].lower()
    
    def test_calculate_posting_frequency(self):
        """Test posting frequency calculation."""
        optimizer = ScheduleOptimizer()
        
        # Test known platforms
        instagram_freq = optimizer._calculate_posting_frequency("instagram")
        assert instagram_freq["posts_per_week"] > 0
        assert instagram_freq["optimal_gap_hours"] > 0
        
        youtube_freq = optimizer._calculate_posting_frequency("youtube")
        assert youtube_freq["posts_per_week"] > 0
        assert youtube_freq["posts_per_week"] < instagram_freq["posts_per_week"]  # YouTube posts less frequently
        
        # Test unknown platform (should have default)
        unknown_freq = optimizer._calculate_posting_frequency("unknown")
        assert unknown_freq["posts_per_week"] > 0
    
    def test_generate_weekly_schedule(self):
        """Test generating complete weekly schedule."""
        optimizer = ScheduleOptimizer()
        
        platforms = ["instagram", "youtube", "tiktok"]
        audience_activity = {
            "peak_hours": ["18:00", "19:00"],
            "peak_days": ["monday", "tuesday", "wednesday"],
        }
        
        result = optimizer.generate_weekly_schedule(
            platforms=platforms,
            audience_activity=audience_activity,
            timezone="UTC",
        )
        
        assert "schedule" in result
        assert len(result["schedule"]) == len(platforms)
        assert result["platforms"] == platforms
        assert result["timezone"] == "UTC"
        assert result["total_posts_per_week"] > 0
        
        # Check each platform has schedule
        for platform in platforms:
            assert platform in result["schedule"]
            platform_schedule = result["schedule"][platform]
            assert "time_slots" in platform_schedule
            assert "posts_per_week" in platform_schedule
            assert "reasoning" in platform_schedule
            assert len(platform_schedule["time_slots"]) == platform_schedule["posts_per_week"]
            
            # Check time slots have required fields
            for slot in platform_schedule["time_slots"]:
                assert "day" in slot
                assert "time" in slot
                assert "slot_number" in slot
    
    def test_all_platforms_have_data(self):
        """Test that all defined platforms have complete data."""
        optimizer = ScheduleOptimizer()
        
        for platform, data in optimizer.PLATFORM_PEAK_TIMES.items():
            assert "weekdays" in data
            assert "times" in data
            assert "timezone" in data
            assert len(data["weekdays"]) > 0
            assert len(data["times"]) > 0
    
    def test_content_type_modifiers_exist(self):
        """Test that content type modifiers are defined."""
        optimizer = ScheduleOptimizer()
        
        assert len(optimizer.CONTENT_TYPE_MODIFIERS) > 0
        
        for content_type, modifiers in optimizer.CONTENT_TYPE_MODIFIERS.items():
            assert "morning_boost" in modifiers
            assert "evening_boost" in modifiers
            assert isinstance(modifiers["morning_boost"], (int, float))
            assert isinstance(modifiers["evening_boost"], (int, float))


# Agent integration tests would go here
# These require database fixtures and are similar to other agent tests
