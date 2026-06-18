"""Tests for Competitor Intelligence Agent and services."""
import pytest
from datetime import datetime, timezone

from app.services.competitors.competitor_scraper import CompetitorScraper
from app.services.competitors.competitor_analyzer import CompetitorAnalyzer


class TestCompetitorScraper:
    """Test CompetitorScraper service."""
    
    @pytest.mark.asyncio
    async def test_scrape_instagram_profile(self):
        """Test Instagram profile scraping (mock mode)."""
        async with CompetitorScraper() as scraper:
            profile = await scraper.scrape_instagram_profile("testuser", max_posts=5)
            
            assert profile["platform"] == "instagram"
            assert profile["username"] == "testuser"
            assert "followers" in profile
            assert "posts" in profile
            assert len(profile["posts"]) <= 5
    
    @pytest.mark.asyncio
    async def test_scrape_youtube_channel(self):
        """Test YouTube channel scraping (mock mode)."""
        async with CompetitorScraper() as scraper:
            channel = await scraper.scrape_youtube_channel("testchannel", max_videos=5)
            
            assert channel["platform"] == "youtube"
            assert channel["channel_id"] == "testchannel"
            assert "subscribers" in channel
            assert "videos" in channel
            assert len(channel["videos"]) <= 5
    
    @pytest.mark.asyncio
    async def test_scrape_tiktok_profile(self):
        """Test TikTok profile scraping (mock mode)."""
        async with CompetitorScraper() as scraper:
            profile = await scraper.scrape_tiktok_profile("testuser", max_videos=5)
            
            assert profile["platform"] == "tiktok"
            assert profile["username"] == "testuser"
            assert "followers" in profile
            assert "videos" in profile
            assert len(profile["videos"]) <= 5
    
    @pytest.mark.asyncio
    async def test_scrape_competitor(self):
        """Test generic competitor scraping."""
        async with CompetitorScraper() as scraper:
            # Test Instagram
            profile = await scraper.scrape_competitor("instagram", "testuser", max_content=3)
            assert profile["platform"] == "instagram"
            
            # Test YouTube
            channel = await scraper.scrape_competitor("youtube", "testchannel", max_content=3)
            assert channel["platform"] == "youtube"
            
            # Test TikTok
            tiktok = await scraper.scrape_competitor("tiktok", "testuser", max_content=3)
            assert tiktok["platform"] == "tiktok"
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_competitors(self):
        """Test batch competitor scraping."""
        async with CompetitorScraper() as scraper:
            competitors = [
                {"platform": "instagram", "username": "user1"},
                {"platform": "youtube", "username": "channel1"},
                {"platform": "tiktok", "username": "user2"},
            ]
            
            results = await scraper.scrape_multiple_competitors(competitors, max_content=3)
            
            assert len(results) == 3
            assert all("platform" in r for r in results)


class TestCompetitorAnalyzer:
    """Test CompetitorAnalyzer service."""
    
    def test_calculate_virality_score_instagram(self):
        """Test virality scoring for Instagram."""
        analyzer = CompetitorAnalyzer()
        
        # High engagement content
        content = {
            "likes": 10000,
            "comments": 500,
            "saves": 1000,
            "shares": 500,
        }
        
        score = analyzer.calculate_virality_score(content, "instagram")
        assert 0 <= score <= 100
        assert score > 70  # Should be high
    
    def test_calculate_virality_score_youtube(self):
        """Test virality scoring for YouTube."""
        analyzer = CompetitorAnalyzer()
        
        content = {
            "views": 100000,
            "likes": 5000,
            "comments": 500,
        }
        
        score = analyzer.calculate_virality_score(content, "youtube")
        assert 0 <= score <= 100
        assert score > 60
    
    def test_calculate_virality_score_tiktok(self):
        """Test virality scoring for TikTok."""
        analyzer = CompetitorAnalyzer()
        
        content = {
            "views": 500000,
            "likes": 50000,
            "comments": 1000,
            "shares": 2000,
        }
        
        score = analyzer.calculate_virality_score(content, "tiktok")
        assert 0 <= score <= 100
        assert score > 70
    
    def test_calculate_engagement_rate(self):
        """Test engagement rate calculation."""
        analyzer = CompetitorAnalyzer()
        
        content = {
            "likes": 1000,
            "comments": 100,
            "saves": 50,
        }
        
        rate = analyzer.calculate_engagement_rate(content, 10000, "instagram")
        assert 0 <= rate <= 1
        assert rate > 0.1  # Should be > 10%
    
    def test_extract_topics(self):
        """Test topic extraction."""
        analyzer = CompetitorAnalyzer()
        
        content = {
            "caption": "Amazing productivity tips for content creators! #productivity #contentcreator #tips",
            "hashtags": ["#productivity", "#contentcreator", "#tips"],
        }
        
        topics = analyzer.extract_topics(content, "instagram")
        assert len(topics) > 0
        assert "productivity" in topics
        assert "contentcreator" in topics
    
    def test_identify_content_gaps(self):
        """Test content gap identification."""
        analyzer = CompetitorAnalyzer()
        
        competitor_content = [
            {
                "caption": "AI tips #ai #productivity",
                "hashtags": ["#ai", "#productivity"],
                "platform": "instagram",
            },
            {
                "caption": "More AI content #ai #tutorial",
                "hashtags": ["#ai", "#tutorial"],
                "platform": "instagram",
            },
        ]
        
        user_content = [
            {
                "caption": "Productivity hacks #productivity",
                "hashtags": ["#productivity"],
                "platform": "instagram",
            },
        ]
        
        gaps = analyzer.identify_content_gaps(competitor_content, user_content)
        assert len(gaps) > 0
        # Should identify "ai" as a gap
        gap_topics = [g["topic"] for g in gaps]
        assert "ai" in gap_topics
    
    def test_analyze_posting_frequency(self):
        """Test posting frequency analysis."""
        analyzer = CompetitorAnalyzer()
        
        content = [
            {"posted_at": datetime.now(timezone.utc).isoformat()}
            for _ in range(10)
        ]
        
        frequency = analyzer.analyze_posting_frequency(content)
        assert "posts_per_week" in frequency
        assert "posts_per_day" in frequency
        assert frequency["posts_per_week"] > 0
    
    def test_generate_steal_idea_brief(self):
        """Test steal idea brief generation."""
        analyzer = CompetitorAnalyzer()
        
        content = {
            "type": "reel",
            "caption": "Amazing AI tips #ai #productivity",
            "hashtags": ["#ai", "#productivity"],
        }
        
        brief = analyzer.generate_steal_idea_brief(content, "instagram", 85)
        assert isinstance(brief, str)
        assert len(brief) > 0
        assert "reel" in brief.lower() or "ai" in brief.lower()
    
    def test_analyze_competitor_profile(self):
        """Test complete profile analysis."""
        analyzer = CompetitorAnalyzer()
        
        profile_data = {
            "platform": "instagram",
            "username": "testuser",
            "followers": 100000,
            "posts": [
                {
                    "id": "post1",
                    "caption": "AI tips #ai #productivity",
                    "hashtags": ["#ai", "#productivity"],
                    "likes": 5000,
                    "comments": 200,
                    "saves": 500,
                },
                {
                    "id": "post2",
                    "caption": "More content #contentcreator",
                    "hashtags": ["#contentcreator"],
                    "likes": 3000,
                    "comments": 150,
                    "saves": 300,
                },
            ],
        }
        
        analysis = analyzer.analyze_competitor_profile(profile_data)
        
        assert analysis["platform"] == "instagram"
        assert analysis["username"] == "testuser"
        assert analysis["content_analyzed"] == 2
        assert "avg_virality_score" in analysis
        assert "avg_engagement_rate" in analysis
        assert "top_performing_content" in analysis
        assert len(analysis["top_performing_content"]) > 0


@pytest.mark.asyncio
async def test_competitor_intelligence_agent_integration(db_session, test_workspace):
    """Integration test for competitor intelligence agent."""
    from app.runtime.orchestration.nodes import competitor_intelligence_agent
    from app.runtime.orchestration.state import AgentState
    
    # Create initial state
    state: AgentState = {
        "workspace_id": str(test_workspace.id),
        "user_niche": "tech",
        "content_pillars": ["AI", "productivity"],
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "content_ideas": [],
        "approval_decisions": {},
        "errors": [],
    }
    
    # Run agent
    result_state = await competitor_intelligence_agent(state, db_session)
    
    # Verify results
    assert "competitor_intelligence" in result_state["active_agents"]
    assert "competitor_intelligence" in result_state["agent_results"]
    
    agent_result = result_state["agent_results"]["competitor_intelligence"]
    
    # Should have analyzed competitors
    assert agent_result.get("competitors_analyzed", 0) > 0
    
    # Should have content analysis
    assert "top_performing_content" in agent_result
    assert isinstance(agent_result["top_performing_content"], list)
    
    # Should have content gaps
    assert "content_gaps" in agent_result
    assert isinstance(agent_result["content_gaps"], list)
    
    # Should generate insights for high-performing content
    if agent_result.get("top_performing_content"):
        high_score_content = [
            c for c in agent_result["top_performing_content"]
            if c.get("virality_score", 0) > 80
        ]
        if high_score_content:
            assert len(result_state["insights"]) > 0
            assert any(i["type"] == "competitor_move" for i in result_state["insights"])
