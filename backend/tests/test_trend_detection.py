"""Tests for Trend Detection Agent and services."""
import pytest
from datetime import datetime, timezone

from app.services.trends.trend_detector import TrendDetector
from app.services.scraping.scraper import WebScraper


class TestTrendDetector:
    """Test TrendDetector service."""
    
    @pytest.mark.asyncio
    async def test_google_trends_mock(self):
        """Test Google Trends fetching (mock mode)."""
        detector = TrendDetector()
        
        keywords = ["AI agents", "content creation"]
        trends = await detector.fetch_google_trends(keywords)
        
        assert len(trends) > 0
        assert all("title" in t for t in trends)
        assert all("source" in t for t in trends)
    
    @pytest.mark.asyncio
    async def test_reddit_trends_mock(self):
        """Test Reddit trends fetching (mock mode)."""
        detector = TrendDetector()
        
        subreddits = ["technology", "productivity"]
        trends = await detector.fetch_reddit_trends(subreddits)
        
        assert len(trends) > 0
        assert all("title" in t for t in trends)
        assert all("subreddit" in t for t in trends)
    
    @pytest.mark.asyncio
    async def test_youtube_trends_mock(self):
        """Test YouTube trends fetching (mock mode)."""
        detector = TrendDetector()
        
        trends = await detector.fetch_youtube_trends()
        
        assert len(trends) > 0
        assert all("title" in t for t in trends)
        assert all("source" in t for t in trends)
    
    @pytest.mark.asyncio
    async def test_tiktok_trends_mock(self):
        """Test TikTok trends fetching (mock mode)."""
        detector = TrendDetector()
        
        trends = await detector.fetch_tiktok_trends()
        
        assert len(trends) > 0
        assert all("title" in t for t in trends)
        assert all("platform" in t for t in trends)
    
    def test_calculate_trend_score(self):
        """Test trend scoring algorithm."""
        detector = TrendDetector()
        
        # High velocity, high volume trend
        score = detector.calculate_trend_score(
            velocity=0.9,
            volume=0.8,
            recency=0.95,
            engagement=0.85,
            diversity=0.7,
        )
        
        assert 0 <= score <= 100
        assert score > 80  # Should be high score
        
        # Low velocity, low volume trend
        score_low = detector.calculate_trend_score(
            velocity=0.2,
            volume=0.1,
            recency=0.3,
            engagement=0.2,
            diversity=0.1,
        )
        
        assert 0 <= score_low <= 100
        assert score_low < 30  # Should be low score
    
    def test_predict_peak_timing(self):
        """Test peak prediction logic."""
        detector = TrendDetector()
        
        # High velocity trend should peak soon
        peak_high = detector.predict_peak_timing(
            velocity=0.9,
            current_volume=0.8,
        )
        
        assert isinstance(peak_high, datetime)
        assert peak_high > datetime.now(timezone.utc)
        
        # Low velocity trend should peak later
        peak_low = detector.predict_peak_timing(
            velocity=0.2,
            current_volume=0.3,
        )
        
        assert isinstance(peak_low, datetime)
        assert peak_low > peak_high  # Should be later than high velocity
    
    @pytest.mark.asyncio
    async def test_fetch_all_trends(self):
        """Test fetching from all sources."""
        detector = TrendDetector()
        
        keywords = ["AI", "productivity"]
        subreddits = ["technology"]
        
        all_trends = await detector.fetch_all_trends(
            niche_keywords=keywords,
            niche_subreddits=subreddits,
        )
        
        assert len(all_trends) > 0
        
        # Should have trends from multiple sources
        sources = set(t.get("source") for t in all_trends)
        assert len(sources) > 1


class TestWebScraper:
    """Test WebScraper service."""
    
    @pytest.mark.asyncio
    async def test_scraper_context_manager(self):
        """Test scraper context manager."""
        async with WebScraper() as scraper:
            assert scraper is not None
            assert scraper._browser is not None
    
    @pytest.mark.skip(reason="Requires live network to example.com.")
    @pytest.mark.asyncio
    async def test_httpx_scraping(self):
        """Test httpx scraping (static sites)."""
        async with WebScraper() as scraper:
            # Test with a simple, reliable site
            html = await scraper.scrape_with_httpx("https://example.com")
            
            assert html is not None
            assert len(html) > 0
            assert "Example Domain" in html
    
    @pytest.mark.skip(reason="Requires live network + Playwright browser.")
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_playwright_scraping(self):
        """Test Playwright scraping (JavaScript sites)."""
        async with WebScraper() as scraper:
            # Test with a simple page
            html = await scraper.scrape_with_playwright(
                "https://example.com",
                timeout=10000,
            )
            
            assert html is not None
            assert len(html) > 0
            assert "Example Domain" in html


@pytest.mark.asyncio
async def test_trend_detection_agent_integration(db_session, test_workspace):
    """Integration test for trend detection agent."""
    from app.runtime.orchestration.nodes import trend_detection_agent
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
    result_state = await trend_detection_agent(state, db_session)
    
    # Verify results
    assert "trend_detection" in result_state["active_agents"]
    assert "trend_detection" in result_state["agent_results"]
    
    agent_result = result_state["agent_results"]["trend_detection"]
    
    # Should have found trends
    assert agent_result.get("trends_found", 0) > 0
    
    # Should have trends list
    assert "trends" in agent_result
    assert isinstance(agent_result["trends"], list)
    
    # Trends should have required fields
    if agent_result["trends"]:
        trend = agent_result["trends"][0]
        assert "title" in trend
        assert "heat_score" in trend
        assert "source" in trend
    
    # Should generate insights for high-scoring trends
    high_score_trends = [t for t in agent_result.get("trends", []) if t.get("heat_score", 0) > 85]
    if high_score_trends:
        assert len(result_state["insights"]) > 0
        assert any(i["type"] == "trend_alert" for i in result_state["insights"])
