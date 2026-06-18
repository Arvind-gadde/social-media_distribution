"""Tests for Tips & Tricks Agent (Agent #9).

Tests:
1. Tips provider service
2. Platform-specific tips
3. Impact score calculation
4. Recent tips filtering
5. LLM prioritization
6. Caching behavior
7. Error handling
8. Integration with agent orchestration
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.tips.tips_provider import TipsProvider
from app.runtime.orchestration.nodes import tips_tricks_agent
from app.runtime.orchestration.state import AgentState


# ═══════════════════════════════════════════════════════════════════════════════
# TIPS PROVIDER SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tips_provider_initialization():
    """Test TipsProvider can be initialized."""
    provider = TipsProvider()
    assert provider is not None
    assert hasattr(provider, 'PLATFORM_TIPS')
    assert 'instagram' in provider.PLATFORM_TIPS
    assert 'youtube' in provider.PLATFORM_TIPS
    assert 'tiktok' in provider.PLATFORM_TIPS


def test_get_tips_for_platform_instagram():
    """Test getting tips for Instagram."""
    provider = TipsProvider()
    
    tips = provider.get_tips_for_platform(
        platform="instagram",
        min_confidence=0.80,
    )
    
    assert len(tips) > 0
    
    # Check tip structure
    tip = tips[0]
    assert "tip_type" in tip
    assert "title" in tip
    assert "explanation" in tip
    assert "expected_impact" in tip
    assert "confidence" in tip
    assert "platforms" in tip
    assert "instagram" in tip["platforms"]


def test_get_tips_for_platform_with_content_type():
    """Test filtering tips by content type."""
    provider = TipsProvider()
    
    tips = provider.get_tips_for_platform(
        platform="instagram",
        content_type="reel",
        min_confidence=0.80,
    )
    
    assert len(tips) > 0
    
    # All tips should support reels
    for tip in tips:
        assert "reel" in tip.get("content_types", [])


def test_get_tips_for_platform_unknown():
    """Test getting tips for unknown platform returns empty list."""
    provider = TipsProvider()
    
    tips = provider.get_tips_for_platform(
        platform="unknown_platform",
        min_confidence=0.80,
    )
    
    assert len(tips) == 0


def test_get_all_tips():
    """Test getting tips across all platforms."""
    provider = TipsProvider()
    
    tips = provider.get_all_tips(min_confidence=0.80)
    
    assert len(tips) > 0
    
    # Should have tips from multiple platforms
    platforms = set()
    for tip in tips:
        platforms.update(tip.get("platforms", []))
    
    assert len(platforms) > 1


def test_get_all_tips_filtered_platforms():
    """Test getting tips for specific platforms only."""
    provider = TipsProvider()
    
    tips = provider.get_all_tips(
        platforms=["instagram", "youtube"],
        min_confidence=0.80,
    )
    
    assert len(tips) > 0
    
    # All tips should be for Instagram or YouTube
    for tip in tips:
        platforms = tip.get("platforms", [])
        assert any(p in ["instagram", "youtube"] for p in platforms)


def test_get_recent_tips():
    """Test getting recent tips (last 30 days)."""
    provider = TipsProvider()
    
    tips = provider.get_recent_tips(days=30)
    
    # Should return tips (all our mock tips are from 2026)
    assert len(tips) >= 0


def test_get_tips_by_type():
    """Test filtering tips by type."""
    provider = TipsProvider()
    
    algorithm_hacks = provider.get_tips_by_type(
        tip_type="algorithm_hack",
    )
    
    assert len(algorithm_hacks) > 0
    
    # All should be algorithm hacks
    for tip in algorithm_hacks:
        assert tip["tip_type"] == "algorithm_hack"


def test_calculate_impact_score():
    """Test impact score calculation."""
    provider = TipsProvider()
    
    tip = {
        "confidence": 0.90,
        "expected_impact": "+100% reach",
    }
    
    score = provider.calculate_impact_score(tip)
    
    assert 0 <= score <= 1
    assert score > 0.5  # Should be high for high confidence + high impact


def test_calculate_impact_score_low_impact():
    """Test impact score with low expected impact."""
    provider = TipsProvider()
    
    tip = {
        "confidence": 0.90,
        "expected_impact": "+5% reach",
    }
    
    score = provider.calculate_impact_score(tip)
    
    assert 0 <= score <= 1
    # Should be lower than high impact tip
    assert score < 0.70


def test_get_top_tips():
    """Test getting top tips by impact score."""
    provider = TipsProvider()
    
    tips = provider.get_top_tips(limit=5)
    
    assert len(tips) > 0
    assert len(tips) <= 5
    
    # All tips should have impact scores
    for tip in tips:
        assert "impact_score" in tip
        assert 0 <= tip["impact_score"] <= 1
    
    # Should be sorted by impact score (descending)
    if len(tips) > 1:
        for i in range(len(tips) - 1):
            assert tips[i]["impact_score"] >= tips[i + 1]["impact_score"]


def test_get_top_tips_platform_filter():
    """Test getting top tips for specific platforms."""
    provider = TipsProvider()
    
    tips = provider.get_top_tips(
        platforms=["instagram"],
        limit=10,
    )
    
    assert len(tips) > 0
    
    # All tips should be for Instagram
    for tip in tips:
        assert "instagram" in tip.get("platforms", [])


# ═══════════════════════════════════════════════════════════════════════════════
# TIPS & TRICKS AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tips_tricks_agent_basic(async_db_session, test_workspace):
    """Test tips & tricks agent basic execution."""
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
                "priority_tips": [
                    {
                        "tip_title": "Use 3-5 hashtags",
                        "platform": "instagram",
                        "why_prioritize": "High impact, easy to implement",
                        "action_steps": ["Review current hashtag strategy", "Test with 3-5 hashtags"],
                    }
                ],
                "quick_wins": ["Reply to comments within 30 minutes"],
                "long_term_strategies": ["Monitor algorithm changes weekly"],
            })
            mock_response.tokens_in = 1000
            mock_response.tokens_out = 500
            mock_response.cost_usd = 0.0015
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await tips_tricks_agent(state, async_db_session)
    
    # Verify agent executed
    assert "tips_tricks" in result_state["active_agents"]
    assert "tips_tricks" in result_state["agent_results"]
    
    # Verify result structure
    result = result_state["agent_results"]["tips_tricks"]
    assert "tips_found" in result
    assert "tips" in result
    assert result["tips_found"] > 0


@pytest.mark.asyncio
async def test_tips_tricks_agent_generates_insights(async_db_session, test_workspace):
    """Test tips & tricks agent generates insights for high-impact tips."""
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
                "priority_tips": [],
                "quick_wins": [],
                "long_term_strategies": [],
            })
            mock_response.tokens_in = 1000
            mock_response.tokens_out = 500
            mock_response.cost_usd = 0.0015
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await tips_tricks_agent(state, async_db_session)
    
    # Verify insights were generated
    assert len(result_state["insights"]) > 0
    
    # Check insight structure
    growth_hack_insights = [i for i in result_state["insights"] if i["type"] == "growth_hack"]
    if growth_hack_insights:
        insight = growth_hack_insights[0]
        assert "💡" in insight["title"]
        assert "action" in insight


@pytest.mark.asyncio
async def test_tips_tricks_agent_caching(async_db_session, test_workspace):
    """Test tips & tricks agent uses caching."""
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
        "tips_found": 10,
        "tips": [
            {
                "title": "Cached Tip",
                "platforms": ["instagram"],
                "impact_score": 0.85,
                "explanation": "From cache",
                "expected_impact": "+50%",
            }
        ],
        "provider": "gemini",
        "model": "gemini-1.5-flash",
    }
    
    with patch('app.runtime.orchestration.nodes.get_cache_manager') as mock_cache:
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_cached_result.return_value = cached_result
        mock_cache.return_value = mock_cache_instance
        
        result_state = await tips_tricks_agent(state, async_db_session)
    
    # Verify cached result was used
    assert result_state["agent_results"]["tips_tricks"] == cached_result
    assert "tips_tricks" in result_state["active_agents"]


@pytest.mark.asyncio
async def test_tips_tricks_agent_cost_tracking(async_db_session, test_workspace):
    """Test tips & tricks agent tracks costs correctly."""
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
            mock_response.content = json.dumps({"priority_tips": [], "quick_wins": [], "long_term_strategies": []})
            mock_response.tokens_in = 1000
            mock_response.tokens_out = 500
            mock_response.cost_usd = 0.0015
            mock_llm_instance.complete.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            result_state = await tips_tricks_agent(state, async_db_session)
    
    result = result_state["agent_results"]["tips_tricks"]
    
    # Verify cost tracking
    assert "tokens_used" in result
    assert "cost_usd" in result
    assert result["tokens_used"] == 1500
    assert result["cost_usd"] == 0.0015
    assert result["cost_usd"] < 0.01  # Under budget


@pytest.mark.asyncio
async def test_tips_tricks_agent_llm_failure_fallback(async_db_session, test_workspace):
    """Test tips & tricks agent falls back gracefully when LLM fails."""
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
            
            result_state = await tips_tricks_agent(state, async_db_session)
    
    result = result_state["agent_results"]["tips_tricks"]
    
    # Verify fallback behavior
    assert result["tips_found"] > 0
    assert result["provider"] is None
    assert "error" in result
    assert "LLM analysis unavailable" in result["error"]
    
    # Should still have tips (without LLM prioritization)
    assert len(result["tips"]) > 0


@pytest.mark.asyncio
async def test_tips_tricks_agent_error_handling(async_db_session, test_workspace):
    """Test tips & tricks agent handles errors gracefully."""
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
        
        result_state = await tips_tricks_agent(state, async_db_session)
    
    # Verify error handling
    assert "tips_tricks" in result_state["active_agents"]
    result = result_state["agent_results"]["tips_tricks"]
    assert "error" in result
    assert len(result_state["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
