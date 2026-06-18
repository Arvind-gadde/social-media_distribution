import json
import uuid

import pytest

from app.services import agent_event_bus


def test_agent_event_channel_and_envelope():
    workspace_id = uuid.uuid4()

    event = agent_event_bus.build_agent_event(
        workspace_id=workspace_id,
        event_type="agent_started",
        agent_type="trend_detection",
        data={"agent_type": "trend_detection"},
        correlation_id="corr-123",
    )

    assert agent_event_bus.agent_event_channel(workspace_id) == (
        f"workspace:{workspace_id}:agent_events"
    )
    assert event["type"] == "agent_started"
    assert event["workspace_id"] == str(workspace_id)
    assert event["agent_type"] == "trend_detection"
    assert event["data"] == {"agent_type": "trend_detection"}
    assert event["correlation_id"] == "corr-123"
    assert "timestamp" in event


@pytest.mark.asyncio
async def test_publish_agent_event_uses_workspace_channel(monkeypatch):
    workspace_id = uuid.uuid4()
    fake_client = _FakeRedis()

    monkeypatch.setattr(
        agent_event_bus.aioredis,
        "from_url",
        lambda *args, **kwargs: fake_client,
    )

    published = await agent_event_bus.publish_agent_event(
        workspace_id=workspace_id,
        event_type="insight_created",
        agent_type="content_research",
        data={"title": "A useful insight"},
    )

    assert published is True
    assert fake_client.closed is True
    assert len(fake_client.published) == 1

    channel, payload = fake_client.published[0]
    assert channel == f"workspace:{workspace_id}:agent_events"

    event = json.loads(payload)
    assert event["type"] == "insight_created"
    assert event["workspace_id"] == str(workspace_id)
    assert event["agent_type"] == "content_research"
    assert event["data"]["title"] == "A useful insight"


@pytest.mark.asyncio
async def test_subscriber_parses_message_and_ignores_invalid_json(monkeypatch):
    workspace_id = uuid.uuid4()
    valid_event = agent_event_bus.build_agent_event(
        workspace_id=workspace_id,
        event_type="agent_completed",
        agent_type="orchestrator",
    )
    fake_pubsub = _FakePubSub([
        {
            "type": "message",
            "channel": agent_event_bus.agent_event_channel(workspace_id),
            "data": json.dumps(valid_event),
        },
        {
            "type": "message",
            "channel": agent_event_bus.agent_event_channel(workspace_id),
            "data": "{not-json",
        },
    ])
    fake_client = _FakeRedis(pubsub=fake_pubsub)

    monkeypatch.setattr(
        agent_event_bus.aioredis,
        "from_url",
        lambda *args, **kwargs: fake_client,
    )

    subscriber = agent_event_bus.AgentEventSubscriber()
    await subscriber.subscribe_workspace(workspace_id)

    assert fake_pubsub.subscribed == [agent_event_bus.agent_event_channel(workspace_id)]
    assert await subscriber.get_event() == valid_event
    assert await subscriber.get_event() is None

    await subscriber.close()
    assert fake_pubsub.closed is True
    assert fake_client.closed is True


class _FakeRedis:
    def __init__(self, pubsub=None):
        self.published = []
        self.closed = False
        self._pubsub = pubsub

    async def publish(self, channel, payload):
        self.published.append((channel, payload))
        return 1

    def pubsub(self, ignore_subscribe_messages=True):
        return self._pubsub or _FakePubSub([])

    async def aclose(self):
        self.closed = True


class _FakePubSub:
    def __init__(self, messages):
        self.messages = list(messages)
        self.subscribed = []
        self.unsubscribed = []
        self.closed = False

    async def subscribe(self, channel):
        self.subscribed.append(channel)

    async def unsubscribe(self, channel):
        self.unsubscribed.append(channel)

    async def get_message(self, timeout=1.0):
        if self.messages:
            return self.messages.pop(0)
        return None

    async def aclose(self):
        self.closed = True
