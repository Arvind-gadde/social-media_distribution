"""Tests for Agent Orchestrator service."""
import pytest
from datetime import datetime, timedelta
from app.services.orchestration.orchestrator import AgentOrchestrator


class TestAgentOrchestrator:
    """Test the AgentOrchestrator service."""
    
    def test_init(self):
        """Test orchestrator initialization."""
        orchestrator = AgentOrchestrator()
        assert orchestrator is not None
        assert orchestrator.total_budget == 0.10
        assert len(orchestrator.AGENT_SCHEDULES) > 0
    
    def test_determine_agents_user_request(self):
        """Test agent determination for user request."""
        orchestrator = AgentOrchestrator()
        
        agents = orchestrator.determine_agents_to_run(
            trigger="user_request",
            user_context={"subscription_tier": "pro"},
        )
        
        assert len(agents) > 0
        assert "trend_detection" in agents
        assert "niche_intelligence" in agents
    
    def test_determine_agents_scheduled(self):
        """Test agent determination for scheduled run."""
        orchestrator = AgentOrchestrator()
        
        # All agents last ran 1 day ago
        last_run_times = {
            agent: datetime.utcnow() - timedelta(days=1)
            for agent in orchestrator.AGENT_SCHEDULES.keys()
        }
        
        agents = orchestrator.determine_agents_to_run(
            trigger="scheduled",
            user_context={"subscription_tier": "pro"},
            last_run_times=last_run_times,
        )
        
        # Daily agents should be included
        assert "analytics_intelligence" in agents
        assert "goal_accountability" in agents
    
    def test_determine_agents_webhook(self):
        """Test agent determination for webhook trigger."""
        orchestrator = AgentOrchestrator()
        
        agents = orchestrator.determine_agents_to_run(
            trigger="webhook",
            user_context={"subscription_tier": "pro"},
        )
        
        assert "collaboration_business" in agents
        assert "analytics_intelligence" in agents
    
    def test_determine_agents_event_post_published(self):
        """Test agent determination for post published event."""
        orchestrator = AgentOrchestrator()
        
        agents = orchestrator.determine_agents_to_run(
            trigger="event",
            user_context={
                "subscription_tier": "pro",
                "event_type": "post_published",
            },
        )
        
        assert "analytics_intelligence" in agents
        assert "predictive_virality" in agents
    
    def test_determine_agents_event_video_uploaded(self):
        """Test agent determination for video uploaded event."""
        orchestrator = AgentOrchestrator()
        
        agents = orchestrator.determine_agents_to_run(
            trigger="event",
            user_context={
                "subscription_tier": "pro",
                "event_type": "video_uploaded",
            },
        )
        
        assert "video_intelligence" in agents
    
    def test_filter_by_subscription_free(self):
        """Test agent filtering for free tier."""
        orchestrator = AgentOrchestrator()
        
        all_agents = list(orchestrator.AGENT_SCHEDULES.keys())
        
        filtered = orchestrator._filter_by_subscription(
            all_agents,
            "free",
        )
        
        # Free tier should have limited agents
        assert len(filtered) < len(all_agents)
        assert "niche_intelligence" in filtered
        assert "trend_detection" in filtered
    
    def test_filter_by_subscription_pro(self):
        """Test agent filtering for pro tier."""
        orchestrator = AgentOrchestrator()
        
        all_agents = list(orchestrator.AGENT_SCHEDULES.keys())
        
        filtered = orchestrator._filter_by_subscription(
            all_agents,
            "pro",
        )
        
        # Pro tier should have all agents
        assert len(filtered) == len(all_agents)
    
    def test_should_run_agent_never_run(self):
        """Test agent should run if never run before."""
        orchestrator = AgentOrchestrator()
        
        should_run = orchestrator._should_run_agent(
            "trend_detection",
            "hourly",
            None,  # Never run
            datetime.utcnow(),
        )
        
        assert should_run is True
    
    def test_should_run_agent_hourly(self):
        """Test hourly agent scheduling."""
        orchestrator = AgentOrchestrator()
        now = datetime.utcnow()
        
        # Last ran 2 hours ago - should run
        should_run = orchestrator._should_run_agent(
            "news_research",
            "hourly",
            now - timedelta(hours=2),
            now,
        )
        assert should_run is True
        
        # Last ran 30 minutes ago - should not run
        should_not_run = orchestrator._should_run_agent(
            "news_research",
            "hourly",
            now - timedelta(minutes=30),
            now,
        )
        assert should_not_run is False
    
    def test_should_run_agent_daily(self):
        """Test daily agent scheduling."""
        orchestrator = AgentOrchestrator()
        now = datetime.utcnow()
        
        # Last ran 2 days ago - should run
        should_run = orchestrator._should_run_agent(
            "analytics_intelligence",
            "daily",
            now - timedelta(days=2),
            now,
        )
        assert should_run is True
        
        # Last ran 12 hours ago - should not run
        should_not_run = orchestrator._should_run_agent(
            "analytics_intelligence",
            "daily",
            now - timedelta(hours=12),
            now,
        )
        assert should_not_run is False
    
    def test_prioritize_agents_within_budget(self):
        """Test agent prioritization when all fit budget."""
        orchestrator = AgentOrchestrator()
        
        agents = ["niche_intelligence", "trend_detection", "analytics_intelligence"]
        
        prioritized = orchestrator.prioritize_agents(agents, 0.10)
        
        # All should fit
        assert len(prioritized) == len(agents)
    
    def test_prioritize_agents_over_budget(self):
        """Test agent prioritization when over budget."""
        orchestrator = AgentOrchestrator()
        
        # All agents
        agents = list(orchestrator.AGENT_SCHEDULES.keys())
        
        # Very limited budget
        prioritized = orchestrator.prioritize_agents(agents, 0.01)
        
        # Should select highest priority agents that fit
        assert len(prioritized) < len(agents)
        # Free agents (cost=0) should be prioritized
        assert "collaboration_business" in prioritized  # Free agent, high priority
        assert "smart_scheduling" in prioritized  # Free agent
    
    def test_track_agent_cost(self):
        """Test cost tracking."""
        orchestrator = AgentOrchestrator()
        
        orchestrator.track_agent_cost("trend_detection", 0.015)
        orchestrator.track_agent_cost("trend_detection", 0.012)
        orchestrator.track_agent_cost("niche_intelligence", 0.005)
        
        assert "trend_detection" in orchestrator.agent_costs
        assert len(orchestrator.agent_costs["trend_detection"]) == 2
    
    def test_get_cost_summary(self):
        """Test cost summary generation."""
        orchestrator = AgentOrchestrator()
        
        orchestrator.track_agent_cost("trend_detection", 0.015)
        orchestrator.track_agent_cost("niche_intelligence", 0.005)
        
        summary = orchestrator.get_cost_summary()
        
        assert "total_cost" in summary
        assert "budget_remaining" in summary
        assert "budget_used_pct" in summary
        assert "agent_costs" in summary
        assert summary["total_cost"] == 0.020
        assert summary["budget_remaining"] == 0.080
    
    def test_should_retry_agent_max_retries(self):
        """Test retry logic with max retries reached."""
        orchestrator = AgentOrchestrator()
        
        should_retry = orchestrator.should_retry_agent(
            "trend_detection",
            Exception("Timeout"),
            retry_count=3,
        )
        
        assert should_retry is False
    
    def test_should_retry_agent_retryable_error(self):
        """Test retry logic with retryable error."""
        orchestrator = AgentOrchestrator()
        
        class TimeoutError(Exception):
            pass
        
        should_retry = orchestrator.should_retry_agent(
            "trend_detection",
            TimeoutError("Connection timeout"),
            retry_count=1,
        )
        
        assert should_retry is True
    
    def test_should_retry_agent_non_retryable_error(self):
        """Test retry logic with non-retryable error."""
        orchestrator = AgentOrchestrator()
        
        class AuthenticationError(Exception):
            pass
        
        should_retry = orchestrator.should_retry_agent(
            "trend_detection",
            AuthenticationError("Invalid API key"),
            retry_count=0,
        )
        
        assert should_retry is False
    
    def test_get_agent_dependencies(self):
        """Test agent dependency retrieval."""
        orchestrator = AgentOrchestrator()
        
        # Agent with dependencies
        deps = orchestrator.get_agent_dependencies("content_ideation")
        assert "trend_detection" in deps
        assert "competitor_intelligence" in deps
        
        # Agent without dependencies
        no_deps = orchestrator.get_agent_dependencies("niche_intelligence")
        assert len(no_deps) == 0
    
    def test_create_execution_plan_no_dependencies(self):
        """Test execution plan with no dependencies."""
        orchestrator = AgentOrchestrator()
        
        agents = ["niche_intelligence", "trend_detection", "analytics_intelligence"]
        
        plan = orchestrator.create_execution_plan(agents)
        
        # All can run in parallel (no dependencies)
        assert len(plan) == 1
        assert len(plan[0]) == 3
    
    def test_create_execution_plan_with_dependencies(self):
        """Test execution plan with dependencies."""
        orchestrator = AgentOrchestrator()
        
        agents = [
            "trend_detection",
            "competitor_intelligence",
            "content_ideation",  # Depends on trend_detection and competitor_intelligence
        ]
        
        plan = orchestrator.create_execution_plan(agents)
        
        # Should have at least 2 batches
        assert len(plan) >= 2
        
        # content_ideation should not be in first batch
        assert "content_ideation" not in plan[0]
    
    def test_agent_priority_sorting(self):
        """Test that agents are sorted by priority."""
        orchestrator = AgentOrchestrator()
        
        agents = orchestrator.determine_agents_to_run(
            trigger="user_request",
            user_context={"subscription_tier": "pro"},
        )
        
        # Check that priorities are descending
        priorities = [
            orchestrator.AGENT_SCHEDULES[agent]["priority"]
            for agent in agents
        ]
        
        assert priorities == sorted(priorities, reverse=True)
