"""Centralized observability bootstrap: Sentry + Prometheus + PostHog.

All three are optional. If credentials are not present at import time the
component is a no-op so the app still boots cleanly in local / test envs.
"""
from __future__ import annotations

import time
from typing import Any, Callable

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


# ─── Sentry ────────────────────────────────────────────────────────────────


def init_sentry() -> bool:
    """Initialize the Sentry SDK. Returns True if Sentry is active."""
    dsn = getattr(settings, "SENTRY_DSN", "")
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        log.warning("sentry_sdk_missing")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.APP_ENV,
        release=getattr(settings, "APP_RELEASE", None) or "contentflow@2.0.0",
        traces_sample_rate=float(getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.05)),
        profiles_sample_rate=float(getattr(settings, "SENTRY_PROFILES_SAMPLE_RATE", 0.0)),
        send_default_pii=False,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    )
    log.info("sentry_initialized", env=settings.APP_ENV)
    return True


# ─── Prometheus ────────────────────────────────────────────────────────────


class _NullMetric:
    def labels(self, *_a, **_k) -> "_NullMetric":
        return self

    def inc(self, *_a, **_k) -> None:
        return None

    def observe(self, *_a, **_k) -> None:
        return None

    def set(self, *_a, **_k) -> None:
        return None


_NULL = _NullMetric()


def _build_metrics() -> dict[str, Any]:
    """Construct Prometheus metric objects or null-doubles."""
    try:
        from prometheus_client import Counter, Histogram, Gauge
    except ImportError:
        log.info("prometheus_client_missing_metrics_disabled")
        return {"http_requests": _NULL, "http_latency": _NULL, "agent_runs": _NULL, "publish_jobs": _NULL, "queue_depth": _NULL}

    http_requests = Counter(
        "contentflow_http_requests_total",
        "HTTP requests by path/method/status",
        ["method", "path", "status"],
    )
    http_latency = Histogram(
        "contentflow_http_request_duration_seconds",
        "HTTP request duration",
        ["method", "path"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
    agent_runs = Counter(
        "contentflow_agent_runs_total",
        "Agent node executions by agent_type / outcome",
        ["agent_type", "outcome"],
    )
    publish_jobs = Counter(
        "contentflow_publish_jobs_total",
        "Publish job lifecycle by platform / status",
        ["platform", "status"],
    )
    queue_depth = Gauge(
        "contentflow_queue_depth",
        "Pending outbox/publish queue depth",
        ["queue"],
    )
    return {
        "http_requests": http_requests,
        "http_latency": http_latency,
        "agent_runs": agent_runs,
        "publish_jobs": publish_jobs,
        "queue_depth": queue_depth,
    }


METRICS: dict[str, Any] = _build_metrics()


def record_agent_run(agent_type: str, outcome: str) -> None:
    METRICS["agent_runs"].labels(agent_type=agent_type, outcome=outcome).inc()


def record_publish_job(platform: str, status: str) -> None:
    METRICS["publish_jobs"].labels(platform=platform, status=status).inc()


def set_queue_depth(queue: str, depth: int) -> None:
    METRICS["queue_depth"].labels(queue=queue).set(depth)


def install_metrics(app) -> None:
    """Mount /metrics and a request-timing middleware on a FastAPI app."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    except ImportError:
        log.info("prometheus_client_missing_skip_install")
        return

    from fastapi import Response
    from starlette.middleware.base import BaseHTTPMiddleware

    class PromMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next: Callable):
            start = time.perf_counter()
            response = await call_next(request)
            elapsed = time.perf_counter() - start
            path = request.scope.get("route").path if request.scope.get("route") else request.url.path
            METRICS["http_requests"].labels(
                method=request.method, path=path, status=str(response.status_code)
            ).inc()
            METRICS["http_latency"].labels(method=request.method, path=path).observe(elapsed)
            return response

    app.add_middleware(PromMiddleware)

    @app.get("/metrics", include_in_schema=False, response_class=Response)
    async def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ─── PostHog ───────────────────────────────────────────────────────────────


_posthog_client: Any | None = None


def init_posthog() -> bool:
    global _posthog_client
    api_key = getattr(settings, "POSTHOG_API_KEY", "")
    if not api_key:
        return False
    try:
        import posthog  # type: ignore
    except ImportError:
        log.info("posthog_missing_skip")
        return False
    posthog.api_key = api_key
    posthog.host = getattr(settings, "POSTHOG_HOST", "https://us.i.posthog.com")
    _posthog_client = posthog
    log.info("posthog_initialized")
    return True


def track_event(distinct_id: str, event: str, properties: dict | None = None) -> None:
    """Fire a PostHog event. Never raises; always logs on failure."""
    if not _posthog_client:
        return
    try:
        _posthog_client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception as exc:  # pragma: no cover - best-effort telemetry
        log.warning("posthog_capture_failed", event=event, error=str(exc))


def init_observability(app) -> dict[str, bool]:
    """Convenience: initialize all three on FastAPI startup. Returns flags."""
    flags = {
        "sentry": init_sentry(),
        "posthog": init_posthog(),
    }
    install_metrics(app)
    flags["prometheus"] = True
    return flags
