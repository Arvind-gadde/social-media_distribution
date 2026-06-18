"""Tests for the with_node_events decorator on agent orchestration nodes."""
import uuid

import pytest

from app.runtime.orchestration import nodes


@pytest.mark.asyncio
async def test_with_node_events_publishes_started_and_completed(monkeypatch):
    workspace_id = str(uuid.uuid4())
    published: list[dict] = []

    async def fake_publish(**kwargs):
        published.append(kwargs)
        return True

    monkeypatch.setattr(nodes, "publish_agent_event", fake_publish)

    @nodes.with_node_events()
    async def sample_agent(state, db):
        state["insights"].append({"x": 1})
        state["insights"].append({"x": 2})
        state["content_ideas"].append({"idea": "A"})
        return state

    state = {
        "workspace_id": workspace_id,
        "correlation_id": "corr-xyz",
        "insights": [],
        "content_ideas": [],
        "errors": [],
    }

    result = await sample_agent(state, db=None)

    assert result is state
    assert [event["event_type"] for event in published] == [
        "agent_node_started",
        "agent_node_completed",
    ]

    started, completed = published
    assert started["agent_type"] == "sample"
    assert started["workspace_id"] == workspace_id
    assert started["correlation_id"] == "corr-xyz"

    assert completed["agent_type"] == "sample"
    assert completed["data"]["insights_added"] == 2
    assert completed["data"]["ideas_added"] == 1
    assert completed["data"]["errors_added"] == 0
    assert completed["data"]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_with_node_events_publishes_failed_and_reraises(monkeypatch):
    workspace_id = str(uuid.uuid4())
    published: list[dict] = []

    async def fake_publish(**kwargs):
        published.append(kwargs)
        return True

    monkeypatch.setattr(nodes, "publish_agent_event", fake_publish)

    @nodes.with_node_events("custom_label")
    async def boom(state, db):
        raise RuntimeError("boom")

    state = {
        "workspace_id": workspace_id,
        "correlation_id": "corr-err",
        "insights": [],
        "content_ideas": [],
        "errors": [],
    }

    with pytest.raises(RuntimeError, match="boom"):
        await boom(state, db=None)

    assert [event["event_type"] for event in published] == [
        "agent_node_started",
        "agent_node_failed",
    ]

    failed = published[1]
    assert failed["agent_type"] == "custom_label"
    assert failed["data"]["error"] == "boom"
    assert failed["data"]["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_with_node_events_skips_publish_without_workspace(monkeypatch):
    published: list[dict] = []

    async def fake_publish(**kwargs):
        published.append(kwargs)
        return True

    monkeypatch.setattr(nodes, "publish_agent_event", fake_publish)

    @nodes.with_node_events()
    async def headless(state, db):
        return state

    await headless({"insights": [], "content_ideas": [], "errors": []}, db=None)

    assert published == []


@pytest.mark.asyncio
async def test_publish_node_progress_emits_progress_event(monkeypatch):
    workspace_id = str(uuid.uuid4())
    published: list[dict] = []

    async def fake_publish(**kwargs):
        published.append(kwargs)
        return True

    monkeypatch.setattr(nodes, "publish_agent_event", fake_publish)

    await nodes.publish_node_progress(
        state={"workspace_id": workspace_id, "correlation_id": "corr-step"},
        agent_type="trend_detection",
        step="fetching_tiktok",
        data={"sources_checked": 3},
    )

    assert len(published) == 1
    event = published[0]
    assert event["event_type"] == "agent_node_progress"
    assert event["agent_type"] == "trend_detection"
    assert event["correlation_id"] == "corr-step"
    assert event["data"]["step"] == "fetching_tiktok"
    assert event["data"]["sources_checked"] == 3
