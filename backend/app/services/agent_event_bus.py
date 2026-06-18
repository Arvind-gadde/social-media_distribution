"""Redis-backed event bus for realtime agent updates."""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


def agent_event_channel(workspace_id: str | uuid.UUID) -> str:
    """Return the Redis pub/sub channel for one workspace."""
    return f"workspace:{workspace_id}:agent_events"


def build_agent_event(
    *,
    workspace_id: str | uuid.UUID,
    event_type: str,
    agent_type: str = "system",
    data: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build the stable event envelope consumed by web clients."""
    event: dict[str, Any] = {
        "type": event_type,
        "workspace_id": str(workspace_id),
        "agent_type": agent_type,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if correlation_id:
        event["correlation_id"] = correlation_id
    return event


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _close_redis_client(client: Any) -> None:
    close = getattr(client, "aclose", None) or getattr(client, "close", None)
    if close:
        await _maybe_await(close())


async def publish_agent_event(
    *,
    workspace_id: str | uuid.UUID,
    event_type: str,
    agent_type: str = "system",
    data: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> bool:
    """Publish an agent event to Redis.

    Event publishing is best-effort: API and worker paths should not fail their
    primary operation just because realtime delivery is temporarily unavailable.
    Failures are logged and reported to the caller as False.
    """
    settings = get_settings()
    client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    event = build_agent_event(
        workspace_id=workspace_id,
        event_type=event_type,
        agent_type=agent_type,
        data=data,
        correlation_id=correlation_id,
    )
    try:
        await client.publish(agent_event_channel(workspace_id), json.dumps(event))
        return True
    except Exception as exc:
        log.warning(
            "agent_event.publish_failed",
            workspace_id=str(workspace_id),
            event_type=event_type,
            error=str(exc),
        )
        return False
    finally:
        await _close_redis_client(client)


class AgentEventSubscriber:
    """Small Redis pub/sub wrapper used by the WebSocket endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._channels: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def channels(self) -> set[str]:
        return set(self._channels)

    async def subscribe_workspace(self, workspace_id: str | uuid.UUID) -> None:
        channel = agent_event_channel(workspace_id)
        async with self._lock:
            if channel in self._channels:
                return
            await self._pubsub.subscribe(channel)
            self._channels.add(channel)

    async def unsubscribe_workspace(self, workspace_id: str | uuid.UUID) -> None:
        channel = agent_event_channel(workspace_id)
        async with self._lock:
            if channel not in self._channels:
                return
            await self._pubsub.unsubscribe(channel)
            self._channels.remove(channel)

    async def get_event(self, timeout: float = 1.0) -> dict[str, Any] | None:
        async with self._lock:
            if not self._channels:
                return None
            message = await self._pubsub.get_message(timeout=timeout)

        if not message or message.get("type") != "message":
            return None

        data = message.get("data")
        if not isinstance(data, str):
            return None

        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            log.warning("agent_event.invalid_json", channel=message.get("channel"))
            return None

        if not isinstance(event, dict):
            return None
        return event

    async def close(self) -> None:
        await _close_redis_client(self._pubsub)
        await _close_redis_client(self._redis)
