"""Tests for Niche Intelligence Agent and services."""
import pytest
from datetime import datetime, timezone

from app.services.niche.niche_analyzer import NicheAnalyzer


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE LAYER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_niche_analyzer_initialization():
    """Test NicheAnalyzer can be initialized."""
    analyzer = NicheAnalyzer()
    assert analyzer is not None


def test_analyze_content_performance_empty():
    """Test analyzing empty content list."""
    analyzer = NicheAnalyzer()
    result = analyzer.analyze_content_performance([])
    
    assert result["total_content"] == 0
    assert result["top_topics"] == []
    assert result["performance_by_topic"] == {}


def test_analyze_content_performance_with_topics():
    """Test analyzing content with topics."""
    analyzer = NicheAnalyzer()
    
    content = [
        {
            "title": "AI Tools Review",
            "topics": ["AI", "tools", "productivity"],
            "views": 1000,
            "likes": 100,
            "comments": 20,
            "shares": 10,
        },
        {
            "title": "More AI Content",
            "topics": ["AI", "machine learning"],
            "views": 800,
            "likes": 80,
            "comments": 15,
            "shares": 5,
        },
        {
            "title": "Productivity Hacks",
            "topics": ["productivity", "tips"],
            "views": 1200,
            "likes": 150,
            "comments": 30,
            "shares": 20,
        },
    ]
    
    result = analyzer.analyze_content_performance(content)
    
    assert result["total_content"] == 3
    assert result["unique_topics"] > 0
    assert len(result["top_topics"]) > 0
    
    # Check AI topic appears (most frequent)
    ai_topic = next((t for t in result["top_topics"] if t["topic"] == "AI"), None)
    assert ai_topic is not None
    assert ai_topic["count"] == 2


def test_analyze_content_performance_without_topics():
    """Test analyzing content without explicit topics (extracts from title)."""
    analyzer = NicheAnalyzer()
    
    content = [
        {
            "title": "Amazing productivity tools for developers",
            "views": 500,
            "likes": 50,
            "comments": 10,
            "shares": 5,
        },
    ]
    
    result = analyzer.analyze_content_performance(content)
    
    assert result["total_content"] == 1
    # Should extract words from title
    assert result["unique_topics"] > 0


def test_identify_content_pillars_empty():
    """Test identifying pillars with no content."""
    analyzer = NicheAnalyzer()
    pillars = analyzer.identify_content_pillars([])
    
    assert pillars == []


def test_identify_content_pillars():
    """Test identifying content pillars."""
    analyzer = NicheAnalyzer()
    
    content = [
        {"title": "AI Post 1", "topics": ["AI"], "views": 1000, "likes": 100, "comments": 10, "shares": 5},
        {"title": "AI Post 2", "topics": ["AI"], "views": 900, "likes": 90, "comments": 9, "shares": 4},
        {"title": "AI Post 3", "topics": ["AI"], "views": 1100, "likes": 110, "comments": 11, "shares": 6},
        {"title": "Tech Post 1", "topics": ["tech"], "views": 500, "likes": 50, "comments": 5, "shares": 2},
        {"title": "Tech Post 2", "topics": ["tech"], "views": 600, "likes": 60, "comments": 6, "shares": 3},
    ]
    
    pillars = analyzer.identify_content_pillars(content, min_content_count=2)
    
    assert len(pillars) > 0
    # AI should be a pillar (3 posts)
    ai_pillar = next((p for p in pillars if p["topic"] == "AI"), None)
    assert ai_pillar is not None
    assert ai_pillar["count"] == 3
    assert "strength_score" in ai_pillar
    assert 0 <= ai_pillar["strength_score"] <= 1


def test_identify_content_pillars_min_count_filter():
    """Test pillar identification respects minimum count."""
    analyzer = NicheAnalyzer()
    
    content = [
        {"title": "Post 1", "topics": ["topic1"], "views": 100, "likes": 10, "comments": 1, "shares": 0},
        {"title": "Post 2", "topics": ["topic2"], "views": 100, "likes": 10, "comments": 1, "shares": 0},
    ]
    
    # With min_count=3, no pillars should be found
    pillars = analyzer.identify_content_pillars(content, min_content_count=3)
    assert len(pillars) == 0


def test_suggest_niche_expansion_no_pillars():
    """Test expansion suggestions with no pillars."""
    analyzer = NicheAnalyzer()
    suggestions = analyzer.suggest_niche_expansion([])
    
    assert len(suggestions) > 0
    assert any("establish pillars" in s["suggestion"].lower() for s in suggestions)


def test_suggest_niche_expansion_few_pillars():
    """Test expansion suggestions with few pillars."""
    analyzer = NicheAnalyzer()
    
    pillars = [
        {"topic": "AI", "count": 5, "strength_score": 0.8, "avg_engagement_rate": 0.12},
    ]
    
    suggestions = analyzer.suggest_niche_expansion(pillars)
    
    assert len(suggestions) > 0
    # Should suggest expanding to 3-5 pillars
    assert any("3-5" in s["suggestion"] for s in suggestions)


def test_suggest_niche_expansion_with_weak_pillar():
    """Test expansion suggestions identifies weak pillars."""
    analyzer = NicheAnalyzer()
    
    pillars = [
        {"topic": "strong", "count": 10, "strength_score": 0.9, "avg_engagement_rate": 0.15},
        {"topic": "weak", "count": 3, "strength_score": 0.3, "avg_engagement_rate": 0.02},
    ]
    
    suggestions = analyzer.suggest_niche_expansion(pillars)
    
    # Should suggest refining weak pillar
    weak_suggestions = [s for s in suggestions if "weak" in s["suggestion"].lower()]
    assert len(weak_suggestions) > 0


def test_suggest_niche_expansion_double_down():
    """Test expansion suggestions recommends doubling down on top performer."""
    analyzer = NicheAnalyzer()
    
    pillars = [
        {"topic": "best_topic", "count": 10, "strength_score": 0.95, "avg_engagement_rate": 0.20},
        {"topic": "other", "count": 5, "strength_score": 0.7, "avg_engagement_rate": 0.10},
    ]
    
    suggestions = analyzer.suggest_niche_expansion(pillars)
    
    # Should suggest doubling down on best topic
    double_down = [s for s in suggestions if "double down" in s["suggestion"].lower()]
    assert len(double_down) > 0
    assert "best_topic" in double_down[0]["suggestion"]


def test_build_audience_interest_graph_empty():
    """Test building interest graph with no content."""
    analyzer = NicheAnalyzer()
    graph = analyzer.build_audience_interest_graph([])
    
    assert graph["interests"] == []
    assert graph["connections"] == []
    assert graph["top_interests"] == []


def test_build_audience_interest_graph():
    """Test building audience interest graph."""
    analyzer = NicheAnalyzer()
    
    content = [
        {"title": "Post 1", "topics": ["AI", "productivity"], "views": 100, "likes": 10, "comments": 1, "shares": 0},
        {"title": "Post 2", "topics": ["AI", "tools"], "views": 100, "likes": 10, "comments": 1, "shares": 0},
        {"title": "Post 3", "topics": ["productivity", "tools"], "views": 100, "likes": 10, "comments": 1, "shares": 0},
    ]
    
    graph = analyzer.build_audience_interest_graph(content)
    
    assert len(graph["interests"]) > 0
    assert len(graph["connections"]) > 0
    assert "total_topics" in graph
    
    # Check AI is in interests (appears twice)
    ai_interest = next((i for i in graph["interests"] if i["topic"] == "AI"), None)
    assert ai_interest is not None
    assert ai_interest["frequency"] == 2


def test_calculate_niche_focus_score_insufficient_data():
    """Test focus score with insufficient data."""
    analyzer = NicheAnalyzer()
    
    # Less than 3 items
    score = analyzer.calculate_niche_focus_score([])
    assert score == 0.5  # Neutral score
    
    score = analyzer.calculate_niche_focus_score([{"title": "Post", "topics": ["topic"]}])
    assert score == 0.5


def test_calculate_niche_focus_score_focused():
    """Test focus score for focused content."""
    analyzer = NicheAnalyzer()
    
    # All content on same topic = high focus
    content = [
        {"title": f"AI Post {i}", "topics": ["AI"], "views": 100, "likes": 10, "comments": 1, "shares": 0}
        for i in range(10)
    ]
    
    score = analyzer.calculate_niche_focus_score(content)
    
    # Should be high (close to 1)
    assert score > 0.7


def test_calculate_niche_focus_score_diverse():
    """Test focus score for diverse content."""
    analyzer = NicheAnalyzer()
    
    # Each post on different topic = low focus
    content = [
        {"title": f"Post {i}", "topics": [f"topic{i}"], "views": 100, "likes": 10, "comments": 1, "shares": 0}
        for i in range(10)
    ]
    
    score = analyzer.calculate_niche_focus_score(content)
    
    # Should be low (close to 0)
    assert score < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_niche_intelligence_agent_basic(test_workspace, db_session):
    """Test basic niche intelligence agent execution."""
    from app.runtime.orchestration.nodes import niche_intelligence_agent
    from app.runtime.orchestration.state import AgentState
    
    state: AgentState = {
        "workspace_id": str(test_workspace.id),
        "user_context": {},
        "trigger": "manual",
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "actions_taken": [],
        "errors": [],
    }
    
    result_state = await niche_intelligence_agent(state, db_session)
    
    assert "niche_intelligence" in result_state["agent_results"]
    assert "niche_intelligence" in result_state["active_agents"]
    
    result = result_state["agent_results"]["niche_intelligence"]
    assert "has_data" in result


@pytest.mark.asyncio
async def test_niche_intelligence_agent_no_content(test_workspace, db_session):
    """Test niche intelligence agent with no content."""
    from app.runtime.orchestration.nodes import niche_intelligence_agent
    from app.runtime.orchestration.state import AgentState
    
    state: AgentState = {
        "workspace_id": str(test_workspace.id),
        "user_context": {},
        "trigger": "manual",
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "actions_taken": [],
        "errors": [],
    }
    
    result_state = await niche_intelligence_agent(state, db_session)
    
    result = result_state["agent_results"]["niche_intelligence"]
    assert result["has_data"] is False
    assert "message" in result


@pytest.mark.asyncio
async def test_niche_intelligence_agent_caching(test_workspace, db_session):
    """Test niche intelligence agent caching."""
    from app.runtime.orchestration.nodes import niche_intelligence_agent
    from app.runtime.orchestration.state import AgentState
    
    state: AgentState = {
        "workspace_id": str(test_workspace.id),
        "user_context": {},
        "trigger": "manual",
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "actions_taken": [],
        "errors": [],
    }
    
    # First call
    result_state1 = await niche_intelligence_agent(state, db_session)
    
    # Second call (should hit cache)
    state2: AgentState = {
        "workspace_id": str(test_workspace.id),
        "user_context": {},
        "trigger": "manual",
        "active_agents": [],
        "agent_results": {},
        "insights": [],
        "actions_taken": [],
        "errors": [],
    }
    result_state2 = await niche_intelligence_agent(state2, db_session)
    
    # Both should have results
    assert "niche_intelligence" in result_state1["agent_results"]
    assert "niche_intelligence" in result_state2["agent_results"]
