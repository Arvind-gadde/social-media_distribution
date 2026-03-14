"""FastAPI application entry point."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIDMiddleware, SecurityHeadersMiddleware,
    app_exception_handler, unhandled_exception_handler,
)
from app.exceptions import AppError
from app.api.v1 import auth, posts, ai, analytics, platforms, notifications

settings = get_settings()
configure_logging(debug=settings.APP_DEBUG)

app = FastAPI(
    title="ContentFlow India",
    description="Multi-platform social media content distribution for Indian creators",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# ── Middleware (order matters — outermost runs first) ─────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────
app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(posts.router, prefix=PREFIX)
app.include_router(ai.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(platforms.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG,
    )
