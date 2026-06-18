"""Integration tests for the /api/v1/agents/ws WebSocket endpoint.

Covers authentication, workspace auto-subscribe, isolation, sub/unsubscribe,
event forwarding, and heartbeat. The Redis subscriber and workspace lookups
are stubbed so the test runs without Redis or a database.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import agents as agents_module


# ─────────────────────────────────────────────────────────────────────────────
# In-memory subscriber replacement
# ─────────────────────────────────────────────────────────────────────────────


class FakeAgentEventSubscriber:
    """Drop-in replacement for AgentEventSubscriber backed by an asyncio.Queue."""

    instances: list["FakeAgentEventSubscriber"] = []

    def __init__(self) -> None:
        self._channels: set[str] = set()
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.subscribe_calls: list[uuid.UUID] = []
        self.unsubscribe_calls: list[uuid.UUID] = []
        self.closed = False
        FakeAgentEventSubscriber.instances.append(self)

    async def subscribe_workspace(self, workspace_id) -> None:
        self.subscribe_calls.append(workspace_id)
        self._channels.add(str(workspace_id))

    async def unsubscribe_workspace(self, workspace_id) -> None:
        self.unsubscribe_calls.append(workspace_id)
        self._channels.discard(str(workspace_id))

    async def get_event(self, timeout: float = 1.0) -> dict[str, Any] | None:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def close(self) -> None:
        self.closed = True

    @property
    def channels(self) -> set[str]:
        return set(self._channels)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def patch_ws_deps(monkeypatch, user_id, workspace_id, other_workspace_id):
    """Patch workspace lookups, decode_token, and AgentEventSubscriber.

    Returns a dict so individual tests can inspect/extend behavior.
    """
    FakeAgentEventSubscriber.instances.clear()

    membership = {str(user_id): {workspace_id}}

    async def fake_workspace_ids(uid: str):
        return list(membership.get(str(uid), set()))

    async def fake_can_access(uid: str, wid):
        return wid in membership.get(str(uid), set())

    def fake_decode_token(token: str, expected_type: str = "access"):
        if token == "valid":
            return {"sub": str(user_id), "type": "access"}
        raise ValueError("invalid token")

    monkeypatch.setattr(agents_module, "_workspace_ids_for_user", fake_workspace_ids)
    monkeypatch.setattr(agents_module, "_user_can_access_workspace", fake_can_access)
    monkeypatch.setattr(agents_module, "decode_token", fake_decode_token)
    monkeypatch.setattr(agents_module, "AgentEventSubscriber", FakeAgentEventSubscriber)

    settings = agents_module.get_settings()
    monkeypatch.setattr(settings, "DEV_BYPASS_AUTH", False, raising=False)

    return {
        "membership": membership,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "other_workspace_id": other_workspace_id,
    }


@pytest.fixture
def app(patch_ws_deps) -> FastAPI:
    """Minimal FastAPI app exposing only the agents router."""
    app = FastAPI()
    app.include_router(agents_module.router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def _drain_until(ws, predicate, max_messages: int = 10) -> dict:
    """Read messages until one satisfies predicate. Fails the test if not seen."""
    for _ in range(max_messages):
        msg = ws.receive_json()
        if predicate(msg):
            return msg
    raise AssertionError(f"predicate never satisfied within {max_messages} messages")


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_rejects_when_no_token_and_no_dev_bypass(client):
    with pytest.raises(Exception):  # WebSocketDisconnect or HTTPException variant
        with client.websocket_connect("/api/v1/agents/ws") as ws:
            ws.receive_json()


def test_ws_rejects_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/agents/ws?token=garbage") as ws:
            ws.receive_json()


# ─────────────────────────────────────────────────────────────────────────────
# Auto-subscribe + connected envelope
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_auto_subscribes_user_workspaces_on_connect(client, patch_ws_deps):
    workspace_id = patch_ws_deps["workspace_id"]

    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        first = ws.receive_json()
        assert first["type"] == "connected"
        assert first["data"]["subscription"] == "added"
        assert first["data"]["workspace_id"] == str(workspace_id)

        summary = ws.receive_json()
        assert summary["type"] == "connected"
        assert summary["data"]["user_id"] == str(patch_ws_deps["user_id"])
        assert str(workspace_id) in summary["data"]["workspace_ids"]

    sub = FakeAgentEventSubscriber.instances[0]
    assert workspace_id in sub.subscribe_calls
    assert sub.closed is True


# ─────────────────────────────────────────────────────────────────────────────
# Workspace isolation
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_subscribe_to_foreign_workspace_is_rejected(client, patch_ws_deps):
    other_workspace_id = patch_ws_deps["other_workspace_id"]

    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        # Drain auto-subscribe greeting
        ws.receive_json()
        ws.receive_json()

        ws.send_json({"type": "subscribe", "workspace_id": str(other_workspace_id)})
        denied = _drain_until(ws, lambda m: m.get("type") == "agent_failed")
        assert denied["data"]["error"] == "workspace_access_denied"
        assert denied["data"]["workspace_id"] == str(other_workspace_id)

    sub = FakeAgentEventSubscriber.instances[0]
    assert other_workspace_id not in sub.subscribe_calls


# ─────────────────────────────────────────────────────────────────────────────
# Subscribe / unsubscribe roundtrip
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_subscribe_and_unsubscribe_own_workspace(client, patch_ws_deps):
    workspace_id = patch_ws_deps["workspace_id"]

    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        ws.receive_json()  # initial subscription added
        ws.receive_json()  # connected summary

        ws.send_json({"type": "unsubscribe", "workspace_id": str(workspace_id)})
        removed = _drain_until(
            ws,
            lambda m: m.get("type") == "connected"
            and m.get("data", {}).get("subscription") == "removed",
        )
        assert removed["data"]["workspace_id"] == str(workspace_id)

        ws.send_json({"type": "subscribe", "workspace_id": str(workspace_id)})
        added = _drain_until(
            ws,
            lambda m: m.get("type") == "connected"
            and m.get("data", {}).get("subscription") == "added",
        )
        assert added["data"]["workspace_id"] == str(workspace_id)

    sub = FakeAgentEventSubscriber.instances[0]
    assert workspace_id in sub.unsubscribe_calls


# ─────────────────────────────────────────────────────────────────────────────
# Event forwarding
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_forwards_published_event_from_redis(client, patch_ws_deps):
    workspace_id = patch_ws_deps["workspace_id"]

    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        ws.receive_json()
        ws.receive_json()

        sub = FakeAgentEventSubscriber.instances[0]
        published = {
            "type": "agent_node_started",
            "workspace_id": str(workspace_id),
            "agent_type": "trend_detection",
            "correlation_id": "corr-1",
            "data": {"agent_type": "trend_detection"},
            "timestamp": "2026-06-17T00:00:00+00:00",
        }
        sub.queue.put_nowait(published)

        forwarded = _drain_until(ws, lambda m: m.get("type") == "agent_node_started")
        assert forwarded["agent_type"] == "trend_detection"
        assert forwarded["correlation_id"] == "corr-1"


# ─────────────────────────────────────────────────────────────────────────────
# Ping / heartbeat
# ─────────────────────────────────────────────────────────────────────────────


def test_ws_ping_returns_heartbeat(client, patch_ws_deps):
    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json({"type": "ping"})
        heartbeat = _drain_until(
            ws,
            lambda m: m.get("type") == "heartbeat" and m.get("data", {}).get("pong"),
        )
        assert heartbeat["data"]["pong"] is True


def test_ws_invalid_json_emits_agent_failed(client, patch_ws_deps):
    with client.websocket_connect("/api/v1/agents/ws?token=valid") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_text("{not json")
        err = _drain_until(
            ws,
            lambda m: m.get("type") == "agent_failed"
            and m.get("data", {}).get("error") == "invalid_json",
        )
        assert err["data"]["error"] == "invalid_json"
