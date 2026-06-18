"""Correlation ID context management for distributed tracing.

Phase 12: Audit & Governance
Every request, agent run, and async task gets a correlation ID that propagates
through the entire execution path for complete traceability.
"""
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable for correlation ID (thread-safe, async-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    correlation_id = _correlation_id.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    _correlation_id.set(correlation_id)


def reset_correlation_id() -> None:
    """Reset correlation ID (useful for testing)."""
    _correlation_id.set(None)


def generate_correlation_id() -> str:
    """Generate and set a new correlation ID."""
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    return correlation_id
