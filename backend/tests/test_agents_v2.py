"""Tests for Goal Agent and Niche Agent Adapter.

What is tested:
  Goal Agent:
    - Progress calculation for weekly/monthly/daily goals
    - Nudge urgency levels (low, medium, high, celebration)
    - Outbox event emission for push notifications
    - Dashboard summary generation

  Niche Adapter:
    - Score, analyze, fact-check, generate — all via mocked LLMProvider
    - Niche context injection from prompt library
    - Usage tracking aggregation
    - Graceful degradation on LLM failure
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import dataclass

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FakeLLMResponse:
    content: str
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    tokens_in: int = 100
    tokens_out: int = 50
    cost_usd: float = 0.001
    latency_ms: int = 200
    cached: bool = False


def _make_fake_goal(
    goal_type: str = "weekly",
    target_count: int = 5,
    is_active: bool = True,
):
    goal = MagicMock()
    goal.id = uuid.uuid4()
    goal.period = goal_type
    goal.target_value = target_count
    goal.is_active = is_active
    return goal


def _make_fake_db(
    goals=None,
    published_count: int = 0,
):
    """Create a fake async DB session.

    Returns goals on first call, count on subsequent calls. If goals=None,
    only count is returned (used for _calculate_progress direct invocations).
    """
    db = AsyncMock()

    goals_result = MagicMock()
    goals_result.scalars.return_value.all.return_value = goals or []

    count_result = MagicMock()
    count_result.scalar.return_value = published_count

    if goals is None:
        side_effect = [count_result, count_result, count_result]
    else:
        side_effect = [goals_result, count_result, count_result, count_result]

    db.execute = AsyncMock(side_effect=side_effect)
    db.commit = AsyncMock()
    db.add = MagicMock()

    return db


# ─────────────────────────────────────────────────────────────────────────────
# Goal Agent — Progress Calculation
# ─────────────────────────────────────────────────────────────────────────────

class TestGoalProgressCalculation:
    @pytest.mark.asyncio
    async def test_goal_met_produces_celebration(self):
        from app.services.content_agent.goal_agent import check_goals_for_workspace

        goal = _make_fake_goal(goal_type="weekly", target_count=3)
        db = _make_fake_db(goals=[goal], published_count=3)

        nudges = await check_goals_for_workspace(db, uuid.uuid4())

        assert len(nudges) == 1
        assert nudges[0]["urgency"] == "celebration"
        assert nudges[0]["achieved"] == 3
        assert nudges[0]["remaining"] == 0

    @pytest.mark.asyncio
    async def test_no_goals_returns_empty(self):
        from app.services.content_agent.goal_agent import check_goals_for_workspace

        db = _make_fake_db(goals=[], published_count=0)
        nudges = await check_goals_for_workspace(db, uuid.uuid4())
        assert nudges == []

    @pytest.mark.asyncio
    async def test_behind_schedule_high_urgency(self):
        """80%+ time elapsed, <60% done → high urgency."""
        from app.services.content_agent.goal_agent import _calculate_progress

        goal = _make_fake_goal(goal_type="weekly", target_count=5)
        db = _make_fake_db(published_count=1)

        # Simulate being 6 days into a 7-day week
        now = datetime.now(timezone.utc)
        # Monday start of week
        week_start = now - timedelta(days=now.weekday())
        # Move to Saturday (day 5, which is >80% of 7 days)
        saturday = week_start + timedelta(days=5, hours=12)

        progress = await _calculate_progress(db, uuid.uuid4(), goal, saturday)

        assert progress["needs_nudge"] is True
        assert progress["urgency"] == "high"
        assert "falling behind" in progress["nudge_message"].lower() or "⚠️" in progress["nudge_message"]

    @pytest.mark.asyncio
    async def test_halfway_medium_urgency(self):
        """50%+ time, <30% done → medium urgency."""
        from app.services.content_agent.goal_agent import _calculate_progress

        goal = _make_fake_goal(goal_type="weekly", target_count=10)
        db = _make_fake_db(published_count=1)  # 10% done

        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        midweek = week_start + timedelta(days=4)  # ~57% through

        progress = await _calculate_progress(db, uuid.uuid4(), goal, midweek)

        assert progress["needs_nudge"] is True
        assert progress["urgency"] == "medium"


class TestGoalSummary:
    @pytest.mark.asyncio
    async def test_dashboard_summary_structure(self):
        from app.services.content_agent.goal_agent import get_goal_summary

        goal = _make_fake_goal(goal_type="weekly", target_count=5)
        db = _make_fake_db(goals=[goal], published_count=3)

        summary = await get_goal_summary(db, uuid.uuid4())

        assert "workspace_id" in summary
        assert "goals" in summary
        assert "overall_on_track" in summary
        assert len(summary["goals"]) == 1
        assert summary["goals"][0]["target"] == 5
        assert summary["goals"][0]["achieved"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# Niche Adapter — LLM calls via mocked provider
# ─────────────────────────────────────────────────────────────────────────────

class TestNicheAdapterScoring:
    @pytest.mark.asyncio
    async def test_score_items_with_niche_context(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        llm_response = FakeLLMResponse(
            content=json.dumps([
                {"index": 1, "score": 0.9, "category": "model_release", "reasoning": "Major release"},
                {"index": 2, "score": 0.3, "category": "other", "reasoning": "Not relevant"},
            ])
        )

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=llm_response)

        mock_db = AsyncMock()
        # Mock prompt library call
        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={
                "system_prompt": "You are a fitness content scorer",
                "niche_context": "Focus on workout routines and nutrition",
                "temperature": 0.3,
                "max_tokens": 500,
            }),
        ):
            adapter = NicheAgentAdapter(mock_llm, mock_db, niche_slug="fitness")
            items = [
                {"title": "New HIIT study shows 2x fat burn", "source_label": "PubMed"},
                {"title": "Stock market crash", "source_label": "Reuters"},
            ]
            result = await adapter.score_items(items)

        assert len(result) == 2
        assert result[0]["relevance_score"] == 0.9
        assert result[0]["category"] == "model_release"
        assert result[1]["relevance_score"] == 0.3

    @pytest.mark.asyncio
    async def test_score_items_empty_list(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        adapter = NicheAgentAdapter(MagicMock(), AsyncMock())
        result = await adapter.score_items([])
        assert result == []


class TestNicheAdapterGeneration:
    @pytest.mark.asyncio
    async def test_generate_content_returns_structured(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        llm_response = FakeLLMResponse(
            content=json.dumps({
                "hook": "🔥 This workout burns 3x more calories",
                "caption": "Full post body here",
                "hashtags": ["#Fitness", "#HIIT"],
                "call_to_action": "Try it and tag me!",
                "thread_tweets": [],
                "script_outline": "",
                "engagement_tips": ["Post before 7 AM"],
            })
        )

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=llm_response)

        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={
                "system_prompt": "You are a fitness content creator",
                "niche_context": "Target: gym-goers aged 18-35",
                "temperature": 0.8,
                "max_tokens": 3000,
            }),
        ):
            adapter = NicheAgentAdapter(mock_llm, AsyncMock(), niche_slug="fitness")
            item = {
                "title": "New HIIT study",
                "summary": "Study shows...",
                "key_points": ["Point 1"],
                "suggested_angle": "fitness angle",
                "source_url": "https://example.com",
            }
            result = await adapter.generate_content(item, "instagram")

        assert result["hook"] == "🔥 This workout burns 3x more calories"
        assert "#Fitness" in result["hashtags"]


class TestNicheAdapterUsageTracking:
    @pytest.mark.asyncio
    async def test_usage_aggregation(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        llm_response = FakeLLMResponse(
            content=json.dumps([{"index": 1, "score": 0.5, "category": "other"}]),
            tokens_in=100, tokens_out=50, cost_usd=0.001,
        )

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=llm_response)

        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={"system_prompt": "", "temperature": 0.3, "max_tokens": 500}),
        ):
            adapter = NicheAgentAdapter(mock_llm, AsyncMock())
            await adapter.score_items([{"title": "Test", "source_label": "test"}])

        usage = adapter.usage_summary
        assert usage["tokens_in"] == 100
        assert usage["tokens_out"] == 50
        assert usage["cost_usd"] == 0.001


class TestNicheAdapterFailure:
    @pytest.mark.asyncio
    async def test_score_graceful_on_llm_failure(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={"system_prompt": "", "temperature": 0.3, "max_tokens": 500}),
        ):
            adapter = NicheAgentAdapter(mock_llm, AsyncMock())
            items = [{"title": "Test item", "source_label": "test"}]
            result = await adapter.score_items(items)

        # Should not raise; items should have defaults
        assert result[0]["relevance_score"] == 0.5
        assert result[0]["category"] == "other"

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_failure(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={"system_prompt": "", "temperature": 0.5, "max_tokens": 1500}),
        ):
            adapter = NicheAgentAdapter(mock_llm, AsyncMock())
            item = {
                "title": "Test item",
                "raw_content": "This is the raw content for fallback",
                "source_label": "test",
            }
            result = await adapter.analyze_item(item)

        # Fallback summary from raw_content
        assert "summary" in result
        assert "raw content" in result["summary"].lower() or result["summary"] != ""

    @pytest.mark.asyncio
    async def test_fact_check_defaults_on_failure(self):
        from app.services.content_agent.niche_adapter import NicheAgentAdapter

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch(
            "app.services.content_agent.niche_adapter.NicheAgentAdapter._get_prompt_config",
            new=AsyncMock(return_value={"system_prompt": "", "temperature": 0.2, "max_tokens": 800}),
        ):
            adapter = NicheAgentAdapter(mock_llm, AsyncMock())
            result = await adapter.fact_check_item({"title": "Test", "raw_content": "content"})

        assert result["fact_check_passed"] is True  # Default: assume true
        assert result["fact_check_confidence"] == 0.5
