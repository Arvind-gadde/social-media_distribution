"""FastAPI application entry point."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIDMiddleware, SecurityHeadersMiddleware,
    app_exception_handler, unhandled_exception_handler,
)
from app.exceptions import AppError
from app.api.v1 import auth, posts, ai, analytics, platforms, notifications, agent, insights
from app.db.session import AsyncSessionLocal
from app.models.models import User

settings = get_settings()
configure_logging(debug=settings.APP_DEBUG)

app = FastAPI(
    title="ContentFlow India",
    description="Multi-platform social media content distribution for Indian creators",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

if getattr(settings, "DEV_BYPASS_AUTH", False):
    from app.core.dev_bypass import DevAuthBypassMiddleware, _DEV_USER_ID
    app.add_middleware(DevAuthBypassMiddleware)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(posts.router,         prefix=PREFIX)
app.include_router(ai.router,            prefix=PREFIX)
app.include_router(analytics.router,     prefix=PREFIX)
app.include_router(platforms.router,     prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(agent.router,         prefix=PREFIX)
app.include_router(insights.router,      prefix=PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}


@app.on_event("startup")
async def ensure_dev_user() -> None:
    if settings.is_production or not getattr(settings, "DEV_BYPASS_AUTH", False):
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == _DEV_USER_ID))
        if result.scalar_one_or_none() is not None:
            return

        db.add(User(
            id=_DEV_USER_ID,
            email="dev@local.dev",
            name="Dev User",
            is_active=True,
            connected_platforms=[],
            encrypted_platform_tokens={},
        ))
        await db.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG,
    )
