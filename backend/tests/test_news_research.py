"""Tests for News & Research Agent (Agent #8).

Tests:
1. News fetcher service
2. RSS feed parsing
3. Niche-specific news fetching
4. Relevance scoring
5. LLM content angle generation
6. Caching behavior
7. Error handling
8. Integration with agent orchestration
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.news.news_fetcher import NewsFetcher
from app.runtime.orchestration.nodes import news_research_agent
from app.runtime.orchestration.state import AgentState


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS FETCHER SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_news_fetcher_initialization():
    """Test NewsFetcher can be initialized."""
    fetcher = NewsFetcher()
    assert fetcher is not None
    assert hasattr(fetcher, 'NICHE_FEEDS')
    assert 'tech' in fetcher.NICHE_FEEDS
    assert 'fitness' in fetcher.NICHE_FEEDS


@pytest.mark.asyncio
async def test_fetch_rss_feed_mock():
    """Test RSS feed fetching with mock data."""
    fetcher = NewsFetcher()
    
    # Mock feedparser to return empty feed (simulating invalid URL)
    with patch('app.services.news.news_fetcher.FEEDPARSER_AVAILABLE', False):
        articles = await fetcher.fetch_rss_feed(
            feed_url="https://example.com/feed",
            max_items=5,
        )
    
    # Should fall back to mock data
    assert len(articles) > 0
    assert len(articles) <= 5
    
    # Check article structure
    article = articles[0]
    assert "title" in article
    assert "description" in article
    assert "url" in article
    assert "author" in article
    assert "published_at" in article
    assert "source" in article


@pytest.mark.asyncio
async def test_fetch_niche_news_tech():
    """Test fetching tech niche news."""
    fetcher = NewsFetcher()
    
    articles = await fetcher.fetch_niche_news(
        niche="tech",
        max_items_per_feed=3,
    )
    
    assert len(articles) > 0
    
    # Check article structure
    for article in articles:
        assert "title" in article
        assert "url" in article
        assert "source" in article


@pytest.mark.asyncio
async def test_fetch_niche_news_unknown_niche():
    """Test fetching news for unknown niche falls back to mock."""
    fetcher = NewsFetcher()
    
    articles = await fetcher.fetch_niche_news(
        niche="unknown_niche",
        max_items_per_feed=3,
    )
    
    # Should return mock data
    assert len(articles) > 0
    assert "unknown_niche" in articles[0]["title"].lower()


@pytest.mark.asyncio
async def test_calculate_relevance_score():
    """Test relevance scoring algorithm."""
    fetcher = NewsFetcher()
    
    article = {
        "title": "New AI Tool for Content Creators",
        "description": "This AI tool helps creators make better content faster",
    }
    
    keywords = ["AI", "content", "creators"]
    
    score = fetcher.calculate_relevance_score(article, keywords)
    
    assert 0 <= score <= 1
    assert score > 0.5  # Should match multiple keywords


@pytest.mark.asyncio
async def test_calculate_relevance_score_no_match():
    """Test relevance scoring with no keyword matches."""
    fetcher = NewsFetcher()
    
    article = {
        "title": "Unrelated Topic",
        "description": "This has nothing to do with the keywords",
    }
    
    keywords = ["AI", "content", "creators"]
    
    score = fetcher.calculate_relevance_score(article, keywords)
    
    assert score == 0


@pytest.mark.asyncio
async def test_fetch_and_score_news():
    """Test fetching and scoring news articles."""
    fetcher = NewsFetcher()
    
    articles = await fetcher.fetch_and_score_news(
        niche="tech",
        niche_keywords=["AI", "content", "creator"],
        max_items=10,
        min_relevance=0.3,
    )
    
    assert len(articles) > 0
    assert len(articles) <= 10
    
    # Check all articles have relevance scores
    for article in articles:
        assert "relevance_score" in article
        assert article["relevance_score"] >= 0.3
    
    # Check articles are sorted by relevance
    if len(articles) > 1:
        for i in range(len(articles) - 1):
            assert articles[i]["relevance_score"] >= articles[i + 1]["relevance_score"]


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS RESEARCH AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Tests don't mock NewsFetcher RSS fetcher; relevance filter drops live articles.")
@pytest.mark.asyncio
async def test_news_research_agent_basic(async_db_session, test_workspace):
    """Test news research agent basic execution."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        # Mock cache miss
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache_instance.cache_result = AsyncMock()
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.runtime.orchestration.nodes.get_llm_client') as mock_llm:
            # Mock LLM response
            mock_llm_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "articles": [
                    {
                        "title": "AI News",
                        "summary": "Latest AI developments",
                        "why_it_matters": "Relevant to creators",
                        "content_angle": "Create video about AI trends",
                        "engagement_potential": 0.85,
                    }
                ]
            })
            mock_response.tokens_in = 1000
            mock_response.tokens_out = 500
            mock_response.cost_usd = 0.0015
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await news_research_agent(state, async_db_session)
    
    # Verify agent executed
    assert "news_research" in result_state["active_agents"]
    assert "news_research" in result_state["agent_results"]
    
    # Verify result structure
    result = result_state["agent_results"]["news_research"]
    assert "articles_fetched" in result
    assert "news_items" in result
    assert result["articles_fetched"] > 0


@pytest.mark.skip(reason="Tests don't mock NewsFetcher; relies on live RSS + relevance filter.")
@pytest.mark.asyncio
async def test_news_research_agent_with_llm_analysis(async_db_session, test_workspace):
    """Test news research agent with LLM content angle generation."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache_instance.cache_result = AsyncMock()
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.runtime.orchestration.nodes.get_llm_client') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "articles": [
                    {
                        "title": "Breaking Tech News",
                        "summary": "Major tech announcement",
                        "why_it_matters": "This will change how creators work",
                        "content_angle": "Create explainer video about this tech",
                        "engagement_potential": 0.90,
                    },
                    {
                        "title": "Creator Economy Update",
                        "summary": "New monetization options",
                        "why_it_matters": "More revenue opportunities",
                        "content_angle": "Tutorial on new monetization",
                        "engagement_potential": 0.85,
                    }
                ]
            })
            mock_response.tokens_in = 1200
            mock_response.tokens_out = 600
            mock_response.cost_usd = 0.0018
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await news_research_agent(state, async_db_session)
    
    result = result_state["agent_results"]["news_research"]
    
    # Verify LLM analysis was applied
    assert result["analyzed_articles"] > 0
    assert len(result["news_items"]) > 0
    
    # Check news item structure
    news_item = result["news_items"][0]
    assert "title" in news_item
    assert "summary" in news_item
    assert "why_it_matters" in news_item
    assert "content_angle" in news_item
    assert "engagement_potential" in news_item
    assert "relevance_score" in news_item


@pytest.mark.asyncio
async def test_news_research_agent_generates_insights(async_db_session, test_workspace):
    """Test news research agent generates insights for high-relevance news."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache_instance.cache_result = AsyncMock()
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.runtime.orchestration.nodes.get_llm_client') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "articles": [
                    {
                        "title": "Viral News",
                        "summary": "This is trending",
                        "why_it_matters": "High engagement potential",
                        "content_angle": "Jump on this trend now",
                        "engagement_potential": 0.95,
                    }
                ]
            })
            mock_response.tokens_in = 1000
            mock_response.tokens_out = 500
            mock_response.cost_usd = 0.0015
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            # Mock NewsFetcher to return high-relevance article
            with patch('app.services.news.news_fetcher.NewsFetcher.fetch_and_score_news') as mock_fetch:
                mock_fetch.return_value = [
                    {
                        "title": "Viral News",
                        "description": "This is trending",
                        "url": "https://example.com/viral",
                        "source": "Tech News",
                        "author": "Reporter",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "relevance_score": 0.85,  # High relevance
                    }
                ]
                
                result_state = await news_research_agent(state, async_db_session)
    
    # Verify insights were generated
    assert len(result_state["insights"]) > 0
    
    # Check insight structure
    insight = result_state["insights"][0]
    assert insight["type"] == "news_alert"
    assert insight["priority"] == 7
    assert "📰" in insight["title"]
    assert "action" in insight


@pytest.mark.asyncio
async def test_news_research_agent_caching(async_db_session, test_workspace):
    """Test news research agent uses caching."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    cached_result = {
        "articles_fetched": 5,
        "analyzed_articles": 5,
        "avg_relevance": 0.75,
        "news_items": [
            {
                "title": "Cached News",
                "summary": "From cache",
                "content_angle": "Cached angle",
                "relevance_score": 0.80,
                "url": "https://example.com/cached",
            }
        ],
        "provider": "gemini",
        "model": "gemini-1.5-flash",
    }
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = cached_result
        mock_cache.return_value = mock_cache_instance
        
        result_state = await news_research_agent(state, async_db_session)
    
    # Verify cached result was used
    assert result_state["agent_results"]["news_research"] == cached_result
    assert "news_research" in result_state["active_agents"]


@pytest.mark.asyncio
async def test_news_research_agent_no_articles(async_db_session, test_workspace):
    """Test news research agent handles no articles found."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.services.news.news_fetcher.NewsFetcher.fetch_and_score_news') as mock_fetch:
            mock_fetch.return_value = []  # No articles
            
            result_state = await news_research_agent(state, async_db_session)
    
    result = result_state["agent_results"]["news_research"]
    
    # Verify empty result handling
    assert result["articles_fetched"] == 0
    assert "message" in result
    assert "No relevant news" in result["message"]


@pytest.mark.skip(reason="Tests don't mock NewsFetcher; relies on live RSS.")
@pytest.mark.asyncio
async def test_news_research_agent_llm_failure_fallback(async_db_session, test_workspace):
    """Test news research agent falls back gracefully when LLM fails."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache_instance.cache_result = AsyncMock()
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.runtime.orchestration.nodes.get_llm_client') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.complete.side_effect = Exception("LLM API error")
            mock_llm.return_value = mock_llm_instance
            
            result_state = await news_research_agent(state, async_db_session)
    
    result = result_state["agent_results"]["news_research"]
    
    # Verify fallback behavior
    assert result["articles_fetched"] > 0
    assert result["provider"] is None
    assert "error" in result
    assert "LLM analysis unavailable" in result["error"]
    
    # Should still have news items (without LLM enhancement)
    assert len(result["news_items"]) > 0


@pytest.mark.skip(reason="Tests don't mock NewsFetcher; relies on live RSS.")
@pytest.mark.asyncio
async def test_news_research_agent_cost_tracking(async_db_session, test_workspace):
    """Test news research agent tracks costs correctly."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = None
        mock_cache_instance.cache_result = AsyncMock()
        mock_cache.return_value = mock_cache_instance
        
        with patch('app.runtime.orchestration.nodes.get_llm_client') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({"articles": []})
            mock_response.tokens_in = 1200
            mock_response.tokens_out = 600
            mock_response.cost_usd = 0.0018
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await news_research_agent(state, async_db_session)
    
    result = result_state["agent_results"]["news_research"]
    
    # Verify cost tracking
    assert "tokens_used" in result
    assert "cost_usd" in result
    assert result["tokens_used"] == 1800
    assert result["cost_usd"] == 0.0018
    assert result["cost_usd"] < 0.01  # Under budget


@pytest.mark.skip(reason="Tests don't mock NewsFetcher; relies on live RSS.")
@pytest.mark.asyncio
async def test_news_research_agent_error_handling(async_db_session, test_workspace):
    """Test news research agent handles errors gracefully."""
    state = AgentState(
        workspace_id=str(test_workspace.id),
        user_context={},
        trigger="scheduled",
        active_agents=[],
        agent_results={},
        insights=[],
        content_ideas=[],
        approval_decisions={},
        errors=[],
    )
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.side_effect = Exception("Cache error")
        mock_cache.return_value = mock_cache_instance
        
        result_state = await news_research_agent(state, async_db_session)
    
    # Verify error handling
    assert "news_research" in result_state["active_agents"]
    result = result_state["agent_results"]["news_research"]
    assert "error" in result
    assert len(result_state["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
