"""Langfuse tracing helpers for LLM calls.

No-op when LANGFUSE_PUBLIC_KEY/SECRET_KEY are unset, so safe to import
unconditionally. Resolves langfuse lazily because the package is optional.
"""
from __future__ import annotations

import contextlib
from typing import Any, Iterator

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

_client: Any = None
_init_attempted = False


def _get_client() -> Any | None:
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True

    settings = get_settings()
    if not settings.has_langfuse:
        return None
    try:
        from langfuse import Langfuse  # type: ignore

        _client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception as exc:  # noqa: BLE001 — langfuse missing or misconfigured
        logger.warning("langfuse.init_failed", error=str(exc))
        _client = None
    return _client


@contextlib.contextmanager
def trace_llm_call(
    *,
    name: str,
    model: str,
    provider: str,
    task_type: str | None,
    workspace_id: str | None,
    input_messages: list[dict[str, str]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Wrap an LLM call in a Langfuse generation span.

    Yields a mutable record dict the caller fills in (output, tokens, cost,
    error). When Langfuse is disabled this is a pure no-op.
    """
    record: dict[str, Any] = {
        "output": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "error": None,
    }
    client = _get_client()
    if client is None:
        yield record
        return

    try:
        trace = client.trace(
            name=name,
            user_id=workspace_id,
            metadata={"task_type": task_type, **(metadata or {})},
        )
        generation = trace.generation(
            name=name,
            model=model,
            model_parameters={"provider": provider},
            input=input_messages,
            metadata=metadata or {},
        )
    except Exception as exc:  # noqa: BLE001 — never let tracing break a call
        logger.warning("langfuse.span_create_failed", error=str(exc))
        yield record
        return

    try:
        yield record
    finally:
        try:
            generation.end(
                output=record.get("output"),
                usage={
                    "input": record.get("tokens_in") or 0,
                    "output": record.get("tokens_out") or 0,
                    "total_cost": record.get("cost_usd") or 0.0,
                },
                level="ERROR" if record.get("error") else "DEFAULT",
                status_message=str(record["error"]) if record.get("error") else None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse.span_end_failed", error=str(exc))


def flush() -> None:
    """Flush pending Langfuse events. Call at process shutdown."""
    client = _get_client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse.flush_failed", error=str(exc))
