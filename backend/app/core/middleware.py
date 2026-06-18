"""Middleware — error handling, security headers, request ID, rate limiting."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.exceptions import AppError

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter with X-RateLimit-* headers.

    Phase 15 Req 9 / 10. Keyed by Bearer token (sub) when present, otherwise client IP.
    Limits skipped for unauthenticated docs/health/websocket paths.
    Falls back to allowing the request if Redis is unreachable.
    """

    SKIP_PATHS = ("/health", "/docs", "/redoc", "/openapi.json")
    WINDOW_SECONDS = 60

    def __init__(self, app, *, authed_limit: int = 300, anon_limit: int = 60) -> None:
        super().__init__(app)
        self.authed_limit = authed_limit
        self.anon_limit = anon_limit
        self._redis = None  # lazy

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                settings = get_settings()
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except Exception:
                self._redis = False  # sentinel for unavailable
        return self._redis or None

    def _identity(self, request: Request) -> tuple[str, int]:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return f"u:{auth[7:][:40]}", self.authed_limit
        cookie = request.cookies.get("cf_access_token")
        if cookie:
            return f"u:{cookie[:40]}", self.authed_limit
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}", self.anon_limit

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)
        if request.url.path.startswith("/ws") or "websocket" in request.url.path:
            return await call_next(request)

        ident, limit = self._identity(request)
        window_start = int(time.time() // self.WINDOW_SECONDS) * self.WINDOW_SECONDS
        reset_at = window_start + self.WINDOW_SECONDS
        bucket_key = f"ratelimit:{ident}:{window_start}"

        redis_client = await self._get_redis()
        remaining = max(limit - 1, 0)
        count = 1

        if redis_client is not None:
            try:
                count = await redis_client.incr(bucket_key)
                if count == 1:
                    await redis_client.expire(bucket_key, self.WINDOW_SECONDS)
                remaining = max(limit - int(count), 0)
            except Exception:
                count = 1
                remaining = max(limit - 1, 0)

        if count > limit:
            retry_after = max(reset_at - int(time.time()), 1)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMITED",
                    "message": "Rate limit exceeded",
                    "limit": limit,
                    "reset_at": reset_at,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        if limit and (limit - remaining) / limit >= 0.8:
            response.headers["X-RateLimit-Warning"] = "approaching limit"
        return response


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert AppError hierarchy to structured JSON responses."""
    logger.warning(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions — never expose internals."""
    logger.error("unhandled_exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )
