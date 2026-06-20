"""Middleware — error handling, security headers, request ID, rate limiting."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
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

    # CSP is intentionally permissive for API responses (no HTML rendered) but
    # set so that misconfigured proxies / docs pages still get a baseline.
    _CSP = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https: wss: ws:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers.setdefault("Content-Security-Policy", self._CSP)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter with X-RateLimit-* headers.

    Keyed by JWT sub (user ID) when present, otherwise client IP.
    Limits skipped for docs/health/websocket paths.
    Falls back to allowing the request if Redis is unreachable.

    Root cause of "too many requests" before this fix:
      - _identity() used the raw Bearer token string (first 40 chars) as the key.
      - Every token refresh created a fresh bucket with a full quota, defeating the limiter,
        but also meant short-lived tokens from SPA refreshes each burned their own 300-req
        bucket independently, causing confusing behaviour when tokens overlapped windows.
      - The fixed-window algorithm allowed a burst of 2× limit across a window boundary.
      - 300 req/min is insufficient for a dashboard with background polling on every page.
    """

    SKIP_PATHS = ("/health", "/docs", "/redoc", "/openapi.json", "/metrics")
    WINDOW_SECONDS = 60
    # Escalating per-IP ban: after this many rate-limit violations within the
    # violation window, the IP is temporarily blocked for BAN_DURATION seconds.
    BAN_VIOLATION_THRESHOLD = 5
    BAN_VIOLATION_WINDOW = 300
    BAN_DURATION = 900

    def __init__(self, app, *, authed_limit: int = 1000, anon_limit: int = 100) -> None:
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
        """Return (bucket_key, limit) for this request.

        Extracts the JWT sub claim (user ID) so all tokens belonging to the same
        user share one rate-limit bucket. Falls back to IP for unauthenticated requests.
        """
        import jwt as _jwt  # PyJWT — already a project dependency

        token: str | None = None
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        elif cookie := request.cookies.get("cf_access_token"):
            token = cookie

        if token:
            try:
                # SECURITY: verify the signature before trusting `sub`. Decoding
                # with verify_signature=False let an attacker forge any sub to
                # mint fresh buckets (evade throttling) or flood a victim's
                # bucket (DoS them). An unverifiable token earns no user bucket.
                settings = get_settings()
                payload = _jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                sub = payload.get("sub")
                if sub:
                    return f"u:{sub}", self.authed_limit
            except Exception:
                pass
            # Forged/expired/malformed token → fall back to the IP anon bucket.

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}", self.anon_limit

    async def _sliding_window(
        self, redis_client, key: str, limit: int, now: float
    ) -> tuple[int, int]:
        """Sliding-window check via Redis sorted set. Returns (count, remaining)."""
        cutoff = now - self.WINDOW_SECONDS
        member = f"{now:.6f}"  # sub-microsecond unique within a single process tick
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, self.WINDOW_SECONDS + 5)
        results = await pipe.execute()
        count: int = results[2]
        remaining = max(limit - count, 0)
        return count, remaining

    async def _record_violation(self, redis_client, ident: str) -> None:
        """Count per-IP rate-limit violations; temporarily ban after the threshold."""
        try:
            vkey = f"rl_viol:{ident}"
            n = await redis_client.incr(vkey)
            if n == 1:
                await redis_client.expire(vkey, self.BAN_VIOLATION_WINDOW)
            if n >= self.BAN_VIOLATION_THRESHOLD:
                await redis_client.set(f"rl_ban:{ident}", "1", ex=self.BAN_DURATION)
                await redis_client.delete(vkey)
                logger.warning("ip_temporarily_banned", ident=ident, duration_s=self.BAN_DURATION)
        except Exception:
            pass

    def _banned_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": "IP_TEMPORARILY_BANNED",
                "message": "Too many requests — this IP is temporarily blocked. Try again later.",
            },
            headers={"Retry-After": str(self.BAN_DURATION)},
        )

    def _rate_limited_response(self, limit: int, reset_at: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": "RATE_LIMITED",
                "message": f"Rate limit exceeded ({limit} req/min). Retry after {self.WINDOW_SECONDS}s.",
                "limit": limit,
                "reset_at": reset_at,
            },
            headers={
                "Retry-After": str(self.WINDOW_SECONDS),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
            },
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)
        if path.startswith("/ws") or "websocket" in path:
            return await call_next(request)

        ident, limit = self._identity(request)
        bucket_key = f"rl2:{ident}"  # rl2 prefix to avoid colliding with old rl: keys
        now = time.time()
        reset_at = int(now) + self.WINDOW_SECONDS

        redis_client = await self._get_redis()
        count, remaining = 1, max(limit - 1, 0)

        if redis_client is not None:
            # Reject IPs currently serving a temporary abuse ban (cheap, up-front).
            if ident.startswith("ip:"):
                try:
                    if await redis_client.exists(f"rl_ban:{ident}"):
                        return self._banned_response()
                except Exception:
                    pass
            try:
                count, remaining = await self._sliding_window(
                    redis_client, bucket_key, limit, now
                )
            except Exception as exc:
                # Fail OPEN: a Redis outage must NOT take the whole API down
                # (including login/register). Allow the request through; the
                # throttle and IP bans resume automatically once Redis returns.
                logger.warning("rate_limiter_redis_unavailable", error=str(exc))
                return await call_next(request)

        if count > limit:
            # Escalate repeat per-IP abuse to a temporary ban.
            if ident.startswith("ip:") and redis_client is not None:
                await self._record_violation(redis_client, ident)
            return self._rate_limited_response(limit, reset_at)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        if limit and (limit - remaining) / limit >= 0.8:
            response.headers["X-RateLimit-Warning"] = "approaching limit"
        return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convert Pydantic RequestValidationError to structured {error, message, fields}."""
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body")
        msg = err.get("msg", "Invalid value")
        if field:
            fields[field] = msg

    message = "; ".join(f"{k}: {v}" for k, v in fields.items()) if fields else "Validation error"
    logger.warning("validation_error", fields=fields, path=request.url.path)
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "message": message, "fields": fields},
    )


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
