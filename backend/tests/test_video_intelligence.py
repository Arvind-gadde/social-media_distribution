"""Tests for Video Intelligence Agent services."""
import pytest
from app.services.video.video_analyzer import VideoAnalyzer


class TestVideoAnalyzer:
    """Test the VideoAnalyzer service."""
    
    def test_init(self):
        """Test analyzer initialization."""
        analyzer = VideoAnalyzer()
        assert analyzer is not None
        assert len(analyzer.STRONG_HOOKS) > 0
    
    def test_analyze_video_basic(self):
        """Test basic video analysis."""
        analyzer = VideoAnalyzer()
        
        result = analyzer.analyze_video(
            video_url="https://example.com/video.mp4",
            duration_seconds=60,
        )
        
        assert result["video_url"] == "https://example.com/video.mp4"
        assert result["duration_seconds"] == 60
        assert "quality_score" in result
        assert "recommendations" in result
    
    def test_analyze_with_transcript(self):
        """Test video analysis with transcript."""
        analyzer = VideoAnalyzer()
        
        transcript = "Watch this amazing tutorial on how to create viral content. You won't believe these 5 tips that will transform your videos."
        
        result = analyzer.analyze_video(
            video_url="https://example.com/video.mp4",
            transcript=transcript,
            duration_seconds=60,
        )
        
        assert result["has_transcript"] is True
        assert "word_count" in result
        assert "hook_text" in result
        assert "hook_score" in result
        assert result["hook_score"] > 0
    
    def test_strong_hook_detection(self):
        """Test strong hook pattern detection."""
        analyzer = VideoAnalyzer()
        
        # Strong hooks
        strong_hooks = [
            "Watch this incredible transformation",
            "You won't believe what happened next",
            "Here's the secret to viral content",
            "5 ways to grow your audience fast",
            "Stop making this mistake",
        ]
        
        for hook in strong_hooks:
            score = analyzer._score_hook(hook)
            assert score >= 0.5, f"Hook '{hook}' should score >= 0.5, got {score}"
    
    def test_weak_hook_detection(self):
        """Test weak hook detection."""
        analyzer = VideoAnalyzer()
        
        weak_hook = "Hello everyone, today I'm going to talk about something"
        score = analyzer._score_hook(weak_hook)
        
        assert score < 0.7  # Weak hooks should score lower
    
    def test_filler_word_detection(self):
        """Test filler word detection."""
        analyzer = VideoAnalyzer()
        
        transcript_with_fillers = "Um, so like, you know, basically what I'm trying to say is, uh, that this is important"
        
        result = analyzer.analyze_video(
            video_url="test.mp4",
            transcript=transcript_with_fillers,
            duration_seconds=10,
        )
        
        assert result["filler_count"] > 0
        assert result["filler_ratio"] > 0
    
    def test_speaking_pace_calculation(self):
        """Test speaking pace calculation."""
        analyzer = VideoAnalyzer()
        
        # 120 words in 60 seconds = 120 WPM
        words = " ".join(["word"] * 120)
        
        result = analyzer.analyze_video(
            video_url="test.mp4",
            transcript=words,
            duration_seconds=60,
        )
        
        assert result["speaking_pace_wpm"] == 120.0
    
    def test_duration_platform_fit(self):
        """Test platform fit based on duration."""
        analyzer = VideoAnalyzer()
        
        # 30 second video - perfect for TikTok/Reels
        result = analyzer.analyze_video(
            video_url="test.mp4",
            duration_seconds=30,
        )
        
        assert "platform_fit" in result
        assert "tiktok" in result["platform_fit"]
        assert result["platform_fit"]["tiktok"] == 1.0
    
    def test_quality_score_calculation(self):
        """Test overall quality score calculation."""
        analyzer = VideoAnalyzer()
        
        # High quality video
        good_transcript = "Watch this! Here are 5 proven tips to grow your audience fast. Let me show you exactly how."
        
        result = analyzer.analyze_video(
            video_url="test.mp4",
            transcript=good_transcript,
            duration_seconds=45,
        )
        
        assert 0 <= result["quality_score"] <= 1
        assert result["quality_score"] > 0.5  # Should be decent quality
    
    def test_recommendations_generation(self):
        """Test recommendation generation."""
        analyzer = VideoAnalyzer()
        
        # Video with issues
        poor_transcript = "Um, so like, hello everyone, uh, today I want to talk about something"
        
        result = analyzer.analyze_video(
            video_url="test.mp4",
            transcript=poor_transcript,
            duration_seconds=10,
        )
        
        assert len(result["recommendations"]) > 0
        assert any("hook" in rec.lower() or "filler" in rec.lower() for rec in result["recommendations"])
    
    def test_suggest_clips(self):
        """Test clip suggestion."""
        analyzer = VideoAnalyzer()
        
        transcript = "This is the introduction. " * 20 + "This is the main content. " * 30 + "This is the conclusion. " * 10
        
        clips = analyzer.suggest_clips(
            transcript=transcript,
            duration_seconds=180,
            target_duration=30,
        )
        
        assert len(clips) > 0
        assert all("start_time" in clip for clip in clips)
        assert all("end_time" in clip for clip in clips)
        assert all("score" in clip for clip in clips)
        assert clips[0]["score"] >= clips[-1]["score"]  # Sorted by score
    
    def test_suggest_clips_empty_transcript(self):
        """Test clip suggestion with empty transcript."""
        analyzer = VideoAnalyzer()
        
        clips = analyzer.suggest_clips(
            transcript="",
            duration_seconds=60,
            target_duration=30,
        )
        
        assert clips == []
    
    def test_generate_caption_suggestions(self):
        """Test caption generation."""
        analyzer = VideoAnalyzer()
        
        transcript = "Want to know the secret to viral content? Here's what nobody tells you. The key is consistency and quality."
        
        captions = analyzer.generate_caption_suggestions(
            transcript=transcript,
            platform="instagram",
        )
        
        assert len(captions) > 0
        assert all(isinstance(caption, str) for caption in captions)
    
    def test_caption_with_question(self):
        """Test caption generation with questions."""
        analyzer = VideoAnalyzer()
        
        transcript = "Are you struggling with content creation? Let me help you solve this problem."
        
        captions = analyzer.generate_caption_suggestions(
            transcript=transcript,
        )
        
        assert len(captions) > 0
        assert any("?" in caption for caption in captions)
    
    def test_platform_recommendations(self):
        """Test platform-specific recommendations."""
        analyzer = VideoAnalyzer()
        
        # Short video
        short_result = analyzer.analyze_video(
            video_url="test.mp4",
            duration_seconds=30,
        )
        
        assert "best_platforms" in short_result
        best_platform = short_result["best_platforms"][0][0]
        assert best_platform in ["tiktok", "instagram_reel", "youtube_short"]
        
        # Long video
        long_result = analyzer.analyze_video(
            video_url="test.mp4",
            duration_seconds=600,  # 10 minutes
        )
        
        best_platform_long = long_result["best_platforms"][0][0]
        assert "youtube" in best_platform_long
    
    def test_hook_with_numbers(self):
        """Test hook scoring with numbers."""
        analyzer = VideoAnalyzer()
        
        hook_with_number = "5 secrets to viral content"
        hook_without_number = "Secrets to viral content"
        
        score_with = analyzer._score_hook(hook_with_number)
        score_without = analyzer._score_hook(hook_without_number)
        
        assert score_with > score_without
    
    def test_hook_with_question(self):
        """Test hook scoring with questions."""
        analyzer = VideoAnalyzer()
        
        hook_with_question = "Want to know the secret?"
        hook_without_question = "Today I will talk about something"
        
        score_with = analyzer._score_hook(hook_with_question)
        score_without = analyzer._score_hook(hook_without_question)
        
        assert score_with > score_without


# Agent integration tests would go here
# These require database fixtures and are similar to other agent tests
