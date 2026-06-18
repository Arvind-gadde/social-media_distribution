"""Tests for Agent Management API endpoints."""
import pytest
pytest.skip(
    "Missing async_client / auth_headers fixtures — HTTP integration setup absent.",
    allow_module_level=True,
)
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.intelligence.models import AgentConfig, AgentInsight, AgentRun
from app.domains.control.models import Workspace


@pytest.mark.asyncio
class TestAgentManagementAPI:
    """Test suite for Agent Management API endpoints."""

    async def test_list_agent_configs_empty(
        self,
        async_client: AsyncClient,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test listing agent configs when none exist."""
        response = await async_client.get(
            "/api/v1/agents",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_agent_configs_with_data(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test listing agent configs with existing data."""
        # Create test agent configs
        configs = [
            AgentConfig(
                workspace_id=test_workspace.id,
                agent_type="niche_intelligence",
                agent_name="Niche Intelligence Agent",
                is_enabled=True,
                run_frequency="every_6h",
                run_count=10,
                success_count=9,
                error_count=1,
            ),
            AgentConfig(
                workspace_id=test_workspace.id,
                agent_type="trend_detection",
                agent_name="Trend Detection Agent",
                is_enabled=False,
                run_frequency="hourly",
                run_count=5,
                success_count=5,
                error_count=0,
            ),
        ]
        for config in configs:
            db_session.add(config)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/agents",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["agent_type"] == "niche_intelligence"
        assert data[0]["is_enabled"] is True
        assert data[0]["run_count"] == 10
        assert data[1]["agent_type"] == "trend_detection"
        assert data[1]["is_enabled"] is False

    async def test_get_agent_status(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test getting overall agent system status."""
        # Create test data
        config1 = AgentConfig(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            is_enabled=True,
        )
        config2 = AgentConfig(
            workspace_id=test_workspace.id,
            agent_type="trend_detection",
            is_enabled=False,
        )
        db_session.add(config1)
        db_session.add(config2)
        await db_session.flush()

        # Create agent runs
        run1 = AgentRun(
            workspace_id=test_workspace.id,
            agent_config_id=config1.id,
            agent_type="niche_intelligence",
            run_type="scheduled",
            status="running",
            correlation_id="test-123",
            total_cost_usd=0.005,
        )
        run2 = AgentRun(
            workspace_id=test_workspace.id,
            agent_config_id=config2.id,
            agent_type="trend_detection",
            run_type="scheduled",
            status="success",
            correlation_id="test-456",
            total_cost_usd=0.010,
        )
        db_session.add(run1)
        db_session.add(run2)
        await db_session.flush()

        # Create insights
        insight = AgentInsight(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            agent_run_id=run1.id,
            title="Test Insight",
            body="Test body",
            is_read=False,
            is_dismissed=False,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/agents/status",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_agents"] == 2
        assert data["enabled_agents"] == 1
        assert data["disabled_agents"] == 1
        assert data["agents_running"] == 1
        assert data["total_runs_today"] == 2
        assert data["total_insights_unread"] == 1
        assert data["cost_today_usd"] == 0.015

    async def test_update_agent_config(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test updating agent configuration."""
        # Create test config
        config = AgentConfig(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            is_enabled=True,
            run_frequency="hourly",
        )
        db_session.add(config)
        await db_session.commit()

        # Update config
        response = await async_client.patch(
            "/api/v1/agents/niche_intelligence",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
            json={
                "is_enabled": False,
                "run_frequency": "daily",
                "config": {"depth": "deep"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert data["run_frequency"] == "daily"
        assert data["config"]["depth"] == "deep"

    async def test_update_agent_config_not_found(
        self,
        async_client: AsyncClient,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test updating non-existent agent config."""
        response = await async_client.patch(
            "/api/v1/agents/nonexistent_agent",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
            json={"is_enabled": False},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_trigger_agent_run(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test manually triggering an agent run."""
        # Create test config
        config = AgentConfig(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            is_enabled=True,
        )
        db_session.add(config)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/agents/niche_intelligence/run",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
            json={"agent_type": "niche_intelligence"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_run_id" in data
        assert data["status"] == "pending"
        assert "queued" in data["message"].lower()

    async def test_trigger_agent_run_disabled(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test triggering a disabled agent."""
        # Create disabled config
        config = AgentConfig(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            is_enabled=False,
        )
        db_session.add(config)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/agents/niche_intelligence/run",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
            json={"agent_type": "niche_intelligence"},
        )
        assert response.status_code == 400
        assert "disabled" in response.json()["detail"].lower()

    async def test_list_agent_insights(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test listing agent insights with pagination."""
        # Create test insights
        insights = []
        for i in range(5):
            insight = AgentInsight(
                workspace_id=test_workspace.id,
                agent_type="niche_intelligence",
                title=f"Insight {i}",
                body=f"Body {i}",
                priority=10 - i,  # Descending priority
                is_read=(i % 2 == 0),  # Alternate read status
                is_dismissed=False,
            )
            insights.append(insight)
            db_session.add(insight)
        await db_session.commit()

        # Test pagination
        response = await async_client.get(
            "/api/v1/agents/insights",
            headers=auth_headers,
            params={
                "workspace_id": str(test_workspace.id),
                "skip": 0,
                "limit": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be sorted by priority descending
        assert data[0]["priority"] == 10
        assert data[1]["priority"] == 9
        assert data[2]["priority"] == 8

    async def test_list_agent_insights_unread_only(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test filtering insights by unread status."""
        # Create mixed insights
        for i in range(3):
            insight = AgentInsight(
                workspace_id=test_workspace.id,
                agent_type="niche_intelligence",
                title=f"Insight {i}",
                body=f"Body {i}",
                is_read=(i == 0),  # Only first one is read
                is_dismissed=False,
            )
            db_session.add(insight)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/agents/insights",
            headers=auth_headers,
            params={
                "workspace_id": str(test_workspace.id),
                "unread_only": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Only unread ones
        assert all(not item["is_read"] for item in data)

    async def test_list_agent_insights_filter_by_type(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test filtering insights by agent type."""
        # Create insights from different agents
        insight1 = AgentInsight(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            title="Niche Insight",
            body="Body",
            is_dismissed=False,
        )
        insight2 = AgentInsight(
            workspace_id=test_workspace.id,
            agent_type="trend_detection",
            title="Trend Insight",
            body="Body",
            is_dismissed=False,
        )
        db_session.add(insight1)
        db_session.add(insight2)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/agents/insights",
            headers=auth_headers,
            params={
                "workspace_id": str(test_workspace.id),
                "agent_type": "niche_intelligence",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["agent_type"] == "niche_intelligence"

    async def test_update_agent_insight(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test updating insight status."""
        # Create test insight
        insight = AgentInsight(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            title="Test Insight",
            body="Body",
            is_read=False,
            is_dismissed=False,
            is_actioned=False,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await async_client.patch(
            f"/api/v1/agents/insights/{insight.id}",
            headers=auth_headers,
            json={
                "is_read": True,
                "is_actioned": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True
        assert data["is_actioned"] is True
        assert data["is_dismissed"] is False

    async def test_update_agent_insight_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test updating non-existent insight."""
        fake_id = uuid4()
        response = await async_client.patch(
            f"/api/v1/agents/insights/{fake_id}",
            headers=auth_headers,
            json={"is_read": True},
        )
        assert response.status_code == 404

    async def test_dismiss_agent_insight(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test dismissing an insight."""
        # Create test insight
        insight = AgentInsight(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            title="Test Insight",
            body="Body",
            is_dismissed=False,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/agents/insights/{insight.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "dismissed" in response.json()["message"].lower()

        # Verify it's marked as dismissed
        await db_session.refresh(insight)
        assert insight.is_dismissed is True

    async def test_get_agent_run(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test getting agent run details."""
        # Create test run
        run = AgentRun(
            workspace_id=test_workspace.id,
            agent_type="niche_intelligence",
            run_type="scheduled",
            status="success",
            correlation_id="test-123",
            total_tokens_used=1000,
            total_cost_usd=0.005,
        )
        db_session.add(run)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/agents/runs/{run.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "niche_intelligence"
        assert data["status"] == "success"
        assert data["tokens_used"] == 1000
        assert data["cost_usd"] == 0.005

    async def test_get_agent_run_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting non-existent agent run."""
        fake_id = uuid4()
        response = await async_client.get(
            f"/api/v1/agents/runs/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_workspace_isolation(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test that workspace isolation works correctly."""
        # Create another workspace
        other_workspace = Workspace(
            name="Other Workspace",
            slug="other-workspace",
            owner_id=test_workspace.owner_id,
        )
        db_session.add(other_workspace)
        await db_session.flush()

        # Create config in other workspace
        config = AgentConfig(
            workspace_id=other_workspace.id,
            agent_type="niche_intelligence",
            is_enabled=True,
        )
        db_session.add(config)
        await db_session.commit()

        # Try to access with test_workspace - should not see it
        response = await async_client.get(
            "/api/v1/agents",
            headers=auth_headers,
            params={"workspace_id": str(test_workspace.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Should not see other workspace's config

    async def test_pagination_limits(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_workspace: Workspace,
        auth_headers: dict,
    ):
        """Test pagination limit enforcement."""
        # Create many insights
        for i in range(150):
            insight = AgentInsight(
                workspace_id=test_workspace.id,
                agent_type="niche_intelligence",
                title=f"Insight {i}",
                body=f"Body {i}",
                is_dismissed=False,
            )
            db_session.add(insight)
        await db_session.commit()

        # Request more than max limit (100)
        response = await async_client.get(
            "/api/v1/agents/insights",
            headers=auth_headers,
            params={
                "workspace_id": str(test_workspace.id),
                "limit": 150,  # Exceeds max
            },
        )
        assert response.status_code == 422  # Validation error
