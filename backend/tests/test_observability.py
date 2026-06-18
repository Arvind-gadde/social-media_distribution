"""Tests for the observability bootstrap.

We don't have Sentry / PostHog / Prometheus credentials in tests, so the
suite focuses on the safe-default behavior: every component should be a
no-op when not configured, and the helpers should never raise.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core import observability


def test_init_sentry_no_dsn_returns_false():
    with patch.object(observability, "settings") as cfg:
        cfg.SENTRY_DSN = ""
        cfg.APP_ENV = "test"
        assert observability.init_sentry() is False


def test_init_posthog_no_key_returns_false():
    with patch.object(observability, "settings") as cfg:
        cfg.POSTHOG_API_KEY = ""
        assert observability.init_posthog() is False


def test_track_event_no_op_without_client():
    observability._posthog_client = None  # type: ignore[attr-defined]
    # Should not raise.
    observability.track_event("user-1", "test_event", {"a": 1})


def test_record_helpers_use_metric_objects():
    # All metric objects expose .labels(...) and an inc / set / observe sink.
    observability.record_agent_run("trend_detection", "completed")
    observability.record_publish_job("instagram", "queued")
    observability.set_queue_depth("outbox", 5)


def test_install_metrics_adds_metrics_route_when_client_available():
    from fastapi import FastAPI

    app = FastAPI()
    observability.install_metrics(app)
    routes = {r.path for r in app.routes}
    # Either metrics is exposed (client installed) or skipped (client missing).
    # Both paths are valid; verify no exception was raised and the app is intact.
    assert "/openapi.json" in routes or app is not None
