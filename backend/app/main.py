"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RateLimitMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware,
    app_exception_handler, unhandled_exception_handler, validation_exception_handler,
)
from app.exceptions import AppError
from fastapi.exceptions import RequestValidationError
from app.api.v1 import auth, ai, analytics, platforms, notifications, agent, oauth, mfa
from app.api.v1 import workspaces, social_accounts, approvals, analytics_api, business, billing
from app.api.v1 import content_projects, workspace_insights
from app.api.v1 import insights as insights_api
from app.api.v1 import audit, usage  # Phase 12: Audit & Governance
from app.api.v1 import platform_webhooks
from app.api.v1.webhooks import stripe_webhooks
# Phase 15: Agent Management API - New comprehensive endpoints
from app.api.v1 import agents, trends, competitors, goals
# Phase 15 frontend-compat routers (match @contentflow/api-client URLs)
from app.api.v1 import inbox as inbox_api
from app.api.v1 import collaborations as collaborations_api
from app.api.v1 import content as content_api
from app.api.v1 import media as media_api
from app.api.v1 import news as news_api
from app.db.session import AsyncSessionLocal
from app.models.models import User

# Phase 12: Correlation ID middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.runtime.correlation import set_correlation_id, generate_correlation_id

settings = get_settings()
configure_logging(debug=settings.APP_DEBUG)

from app.core.observability import init_observability  # noqa: E402  (post-config)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to extract or generate correlation IDs for request tracing.
    
    Phase 12: Audit & Governance
    Every request gets a correlation ID that propagates through the entire
    execution path (API -> workers -> providers) for complete traceability.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()
        else:
            set_correlation_id(correlation_id)
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


app = FastAPI(
    title="ContentFlow AI",
    description="AI-Powered Creator Operating System — From Idea to Viral",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

if not settings.is_production and getattr(settings, "DEV_BYPASS_AUTH", False):
    from app.core.dev_bypass import DevAuthBypassMiddleware, _DEV_USER_ID
    app.add_middleware(DevAuthBypassMiddleware)

# CORS must be added FIRST (last in execution order due to middleware stack).
# Wildcards removed — explicit method/header allow-list keeps the attack
# surface minimal even if a CORS bypass is later discovered in the framework.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Correlation-ID",
        "X-Request-ID",
        "X-Workspace-Id",
        "X-CSRF-Token",
    ],
    expose_headers=[
        "X-Correlation-ID",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,
)
# Phase 12: Add correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

_observability_flags = init_observability(app)

PREFIX = "/api/v1"
# Legacy routers (to be migrated to workspace-scoping)
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(mfa.router,           prefix=PREFIX)
# posts router disabled — legacy, superseded by content_projects + content (PostRepository removed)
app.include_router(ai.router,            prefix=PREFIX)
app.include_router(analytics.router,     prefix=PREFIX)
app.include_router(platforms.router,     prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(agent.router,         prefix=PREFIX)
app.include_router(insights_api.router,  prefix=PREFIX)

# v2 workspace-aware routers
app.include_router(oauth.router,               prefix=PREFIX)
app.include_router(workspaces.router,          prefix=PREFIX)
app.include_router(content_projects.router,    prefix=PREFIX)
app.include_router(workspace_insights.router,  prefix=PREFIX)
app.include_router(social_accounts.router,     prefix=PREFIX)
app.include_router(approvals.router,           prefix=PREFIX)
app.include_router(analytics_api.router,       prefix=PREFIX)
app.include_router(platform_webhooks.router,   prefix=PREFIX)
app.include_router(business.router,            prefix=PREFIX)
app.include_router(billing.router,             prefix=PREFIX)
app.include_router(stripe_webhooks.router,     prefix=PREFIX)
# Phase 12: Audit & Governance
app.include_router(audit.router,               prefix=PREFIX)
app.include_router(usage.router,               prefix=PREFIX)
# Phase 15: Agent Management API - Complete agent orchestration endpoints
app.include_router(agents.router,              prefix=PREFIX)
app.include_router(trends.router,              prefix=PREFIX)
app.include_router(competitors.router,         prefix=PREFIX)
app.include_router(goals.router,               prefix=PREFIX)
# Phase 15 frontend-compat routers
app.include_router(inbox_api.router,                   prefix=PREFIX)
app.include_router(collaborations_api.router,          prefix=PREFIX)
app.include_router(content_api.projects_router,        prefix=PREFIX)
app.include_router(content_api.ideas_router,           prefix=PREFIX)
app.include_router(media_api.router,                   prefix=PREFIX)
app.include_router(news_api.router,                    prefix=PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "2.0.0", "env": settings.APP_ENV}


@app.on_event("startup")
async def seed_niches_on_startup() -> None:
    """Seed niche definitions if the table is empty."""
    from app.domains.control.models import Niche
    from app.domains.control.seed_niches import seed_niches
    import structlog

    logger = structlog.get_logger("startup")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Niche).limit(1))
            if result.scalar_one_or_none() is None:
                count = await seed_niches(db)
                logger.info("niches_seeded", count=count)
            else:
                logger.info("niches_already_seeded")
    except Exception as exc:
        # Don't crash app if niches table doesn't exist yet (pre-migration)
        logger.warning("niche_seed_skipped", error=str(exc))


@app.on_event("startup")
async def seed_intelligence_on_startup() -> None:
    """Seed provider policies and prompt catalog if tables are empty."""
    from app.domains.intelligence.models import ProviderPolicy, PromptCatalog
    from app.domains.intelligence.seed_policies import (
        seed_provider_policies, seed_prompt_catalog,
    )
    import structlog

    logger = structlog.get_logger("startup")

    try:
        async with AsyncSessionLocal() as db:
            pp_result = await db.execute(select(ProviderPolicy).limit(1))
            if pp_result.scalar_one_or_none() is None:
                count = await seed_provider_policies(db)
                logger.info("provider_policies_seeded", count=count)
            else:
                logger.info("provider_policies_already_seeded")

            pc_result = await db.execute(select(PromptCatalog).limit(1))
            if pc_result.scalar_one_or_none() is None:
                count = await seed_prompt_catalog(db)
                logger.info("prompt_catalog_seeded", count=count)
            else:
                logger.info("prompt_catalog_already_seeded")
    except Exception as exc:
        logger.warning("intelligence_seed_skipped", error=str(exc))


@app.on_event("startup")
async def bootstrap_qdrant_collections() -> None:
    """Ensure all Qdrant collections exist before agents try to use them."""
    if not settings.has_qdrant:
        return

    from app.services.niche.qdrant_store import QdrantStore
    import structlog

    logger = structlog.get_logger("startup")

    collections = (
        settings.QDRANT_COLLECTION_NICHE,
        settings.QDRANT_COLLECTION_CONTENT,
        settings.QDRANT_COLLECTION_DOCUMENTS,
    )
    for name in collections:
        try:
            await QdrantStore(collection=name).ensure_collection()
            logger.info("qdrant_collection_ready", collection=name)
        except Exception as exc:  # don't crash the app on Qdrant outage
            logger.warning("qdrant_bootstrap_failed", collection=name, error=str(exc))


@app.on_event("startup")
async def seed_niche_sources_on_startup() -> None:
    """Seed source registry from niche source_config if empty."""
    from app.domains.intelligence.models import SourceRegistry
    from app.domains.intelligence.seed_sources import seed_niche_sources
    import structlog

    logger = structlog.get_logger("startup")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SourceRegistry).limit(1))
            if result.scalar_one_or_none() is None:
                count = await seed_niche_sources(db)
                logger.info("niche_sources_seeded", count=count)
            else:
                logger.info("niche_sources_already_seeded")
    except Exception as exc:
        logger.warning("niche_source_seed_skipped", error=str(exc))


@app.on_event("startup")
async def ensure_dev_user() -> None:
    """Create dev user + workspace for local development."""
    if settings.is_production or not getattr(settings, "DEV_BYPASS_AUTH", False):
        return

    from app.domains.control.models import Workspace, WorkspaceMembership, WorkspaceRole, InviteStatus
    from datetime import datetime, timezone
    import structlog

    logger = structlog.get_logger("startup")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == _DEV_USER_ID))
        if result.scalar_one_or_none() is not None:
            return

        # Create dev user
        user = User(
            id=_DEV_USER_ID,
            email="dev@local.dev",
            name="Dev User",
            username="devuser",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create dev workspace
        workspace = Workspace(
            name="Dev Workspace",
            slug="dev-workspace",
            owner_id=_DEV_USER_ID,
        )
        db.add(workspace)
        await db.flush()

        # Create membership
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=_DEV_USER_ID,
            role=WorkspaceRole.OWNER,
            invite_status=InviteStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
        )
        db.add(membership)
        await db.commit()
        logger.info("dev_user_created", user_id=str(_DEV_USER_ID), workspace_id=str(workspace.id))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG,
    )
