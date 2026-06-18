"""Analytics sync worker — pulls engagement metrics from connected platforms.

Periodically fetches post-level analytics from connected social accounts
and writes append-only AnalyticsFact rows. Enables time-series tracking
of engagement without losing historical data.

Called by Celery beat schedule (every 4 hours).

Flow:
  1. Find all active social accounts with valid tokens
  2. For each, find recently published content (via PublishJob.platform_post_id)
  3. Fetch metrics from platform API
  4. Write AnalyticsFact rows (append-only, one per measurement time)
  5. Update SocialAccount follower/engagement stats
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import SocialAccount, TokenStatus
from app.domains.execution.models import (
    PublishJob, PublishStatus, AnalyticsFact,
)

logger = structlog.get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def sync_analytics_for_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> dict[str, int]:
    """Sync analytics for all active social accounts in a workspace.

    Returns summary of posts synced and facts written.
    """
    # Get active social accounts with valid tokens
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.workspace_id == workspace_id,
            SocialAccount.is_active == True,
            SocialAccount.token_status == TokenStatus.VALID,
        )
    )
    accounts = result.scalars().all()

    total_facts = 0
    total_posts = 0

    for account in accounts:
        try:
            facts, posts = await _sync_account_analytics(db, account)
            total_facts += facts
            total_posts += posts
        except Exception as exc:
            logger.error(
                "analytics_sync_account_failed",
                account_id=str(account.id),
                platform=account.platform,
                error=str(exc),
            )

    if total_facts > 0:
        await db.commit()

    return {"facts_written": total_facts, "posts_synced": total_posts}


async def _sync_account_analytics(
    db: AsyncSession,
    account: SocialAccount,
) -> tuple[int, int]:
    """Sync analytics for a single social account.

    Returns (facts_written, posts_synced).
    """
    # Find recently published posts through this account
    lookback = _utcnow() - timedelta(days=30)
    result = await db.execute(
        select(PublishJob).where(
            PublishJob.social_account_id == account.id,
            PublishJob.status == PublishStatus.COMPLETED,
            PublishJob.completed_at >= lookback,
            PublishJob.platform_post_id.isnot(None),
        )
        .order_by(PublishJob.completed_at.desc())
        .limit(50)
    )
    published_jobs = result.scalars().all()

    if not published_jobs:
        return 0, 0

    # Fetch metrics from platform
    platform_metrics = await _fetch_platform_metrics(
        account, [job.platform_post_id for job in published_jobs],
    )

    facts_written = 0
    now = _utcnow()

    for job in published_jobs:
        metrics = platform_metrics.get(job.platform_post_id)
        if not metrics:
            continue

        # Write AnalyticsFact (append-only — never update existing)
        fact = AnalyticsFact(
            workspace_id=job.workspace_id,
            content_variant_id=job.content_variant_id,
            social_account_id=account.id,
            platform=account.platform,
            recorded_at=now,
            views=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            saves=metrics.get("saves", 0),
            reach=metrics.get("reach", 0),
            impressions=metrics.get("impressions", 0),
            engagement_rate=_calc_engagement_rate(metrics) or 0.0,
            completion_rate=metrics.get("completion_rate"),
            avg_watch_time_seconds=metrics.get("avg_watch_time"),
            link_clicks=metrics.get("clicks", 0),
            profile_visits=metrics.get("profile_visits", 0),
        )
        db.add(fact)
        facts_written += 1

    # Update account-level stats
    await _update_account_stats(db, account)

    return facts_written, len(published_jobs)


async def _fetch_platform_metrics(
    account: SocialAccount,
    post_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch engagement metrics from a platform API.

    Args:
        account: Social account with encrypted tokens
        post_ids: List of platform-specific post IDs

    Returns:
        Dict mapping post_id → metrics dict

    TODO: Implement per-platform API calls:
      - Instagram: GET /{media-id}/insights
      - YouTube: GET /videos?part=statistics
      - Twitter: GET /2/tweets?ids=...&tweet.fields=public_metrics
      - LinkedIn: GET /organizationalEntityShareStatistics
    """
    # For now, return empty — real implementation after OAuth flows
    metrics: dict[str, dict[str, Any]] = {}

    if account.platform == "instagram":
        metrics = await _fetch_instagram_metrics(account, post_ids)
    elif account.platform == "youtube":
        metrics = await _fetch_youtube_metrics(account, post_ids)
    elif account.platform == "twitter":
        metrics = await _fetch_twitter_metrics(account, post_ids)
    elif account.platform == "linkedin":
        metrics = await _fetch_linkedin_metrics(account, post_ids)

    return metrics


async def _fetch_instagram_metrics(
    account: SocialAccount,
    post_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch Instagram post insights via Graph API."""
    try:
        import httpx
        from app.services.token_vault import get_vault

        if not account.encrypted_access_token:
            return {}
        
        # Decrypt token
        vault = get_vault()
        token = vault.decrypt(account.encrypted_access_token, account.workspace_id)
        if not token:
            return {}

        metrics: dict[str, dict[str, Any]] = {}
        api_base = "https://graph.facebook.com/v19.0"

        async with httpx.AsyncClient(timeout=30) as client:
            for post_id in post_ids[:25]:  # Rate limit safety
                try:
                    # Get basic metrics
                    resp = await client.get(
                        f"{api_base}/{post_id}",
                        params={
                            "fields": "like_count,comments_count,timestamp",
                            "access_token": token,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        metrics[post_id] = {
                            "likes": data.get("like_count", 0),
                            "comments": data.get("comments_count", 0),
                        }

                    # Get insights (reach, impressions, saves)
                    insights_resp = await client.get(
                        f"{api_base}/{post_id}/insights",
                        params={
                            "metric": "reach,impressions,saved",
                            "access_token": token,
                        },
                    )
                    if insights_resp.status_code == 200:
                        for metric_data in insights_resp.json().get("data", []):
                            name = metric_data.get("name")
                            value = metric_data.get("values", [{}])[0].get("value", 0)
                            if post_id in metrics:
                                metrics[post_id][name] = value
                except Exception:
                    continue

        return metrics
    except ImportError:
        return {}


async def _fetch_youtube_metrics(
    account: SocialAccount,
    post_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch YouTube video statistics via Data API v3."""
    try:
        import httpx
        from app.services.token_vault import get_vault

        if not account.encrypted_access_token:
            return {}
        
        # Decrypt token
        vault = get_vault()
        token = vault.decrypt(account.encrypted_access_token, account.workspace_id)
        if not token:
            return {}

        metrics: dict[str, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            # Batch request (up to 50 video IDs)
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(post_ids[:50]),
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    vid = item["id"]
                    stats = item.get("statistics", {})
                    metrics[vid] = {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "shares": 0,  # Not available in YouTube API
                    }

        return metrics
    except ImportError:
        return {}


async def _fetch_twitter_metrics(
    account: SocialAccount,
    post_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch tweet metrics via Twitter API v2."""
    try:
        import httpx
        from app.services.token_vault import get_vault

        if not account.encrypted_access_token:
            return {}
        
        # Decrypt token
        vault = get_vault()
        token = vault.decrypt(account.encrypted_access_token, account.workspace_id)
        if not token:
            return {}

        metrics: dict[str, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            # Batch up to 100 tweet IDs
            resp = await client.get(
                "https://api.twitter.com/2/tweets",
                params={
                    "ids": ",".join(post_ids[:100]),
                    "tweet.fields": "public_metrics",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                for tweet in resp.json().get("data", []):
                    tid = tweet["id"]
                    pm = tweet.get("public_metrics", {})
                    metrics[tid] = {
                        "views": pm.get("impression_count", 0),
                        "likes": pm.get("like_count", 0),
                        "comments": pm.get("reply_count", 0),
                        "shares": pm.get("retweet_count", 0) + pm.get("quote_count", 0),
                    }

        return metrics
    except ImportError:
        return {}


async def _fetch_linkedin_metrics(
    account: SocialAccount,
    post_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch LinkedIn post metrics."""
    # LinkedIn analytics require organization-level access
    # and a more complex OAuth flow
    return {}


def _calc_engagement_rate(metrics: dict[str, Any]) -> float | None:
    """Calculate engagement rate from raw metrics."""
    interactions = (
        metrics.get("likes", 0)
        + metrics.get("comments", 0)
        + metrics.get("shares", 0)
        + metrics.get("saves", 0)
    )
    views = metrics.get("views") or metrics.get("impressions") or metrics.get("reach")
    if views and views > 0:
        return round(interactions / views, 6)
    return None


async def _update_account_stats(
    db: AsyncSession,
    account: SocialAccount,
) -> None:
    """Update account-level engagement stats from recent analytics."""
    # Calculate average engagement rate from last 30 days
    lookback = _utcnow() - timedelta(days=30)
    result = await db.execute(
        select(func.avg(AnalyticsFact.engagement_rate)).where(
            AnalyticsFact.social_account_id == account.id,
            AnalyticsFact.recorded_at >= lookback,
            AnalyticsFact.engagement_rate.isnot(None),
        )
    )
    avg_rate = result.scalar()

    if avg_rate is not None:
        await db.execute(
            update(SocialAccount)
            .where(SocialAccount.id == account.id)
            .values(
                engagement_rate=round(float(avg_rate), 6),
                last_synced_at=_utcnow(),
            )
        )


async def sync_all_workspaces(db: AsyncSession) -> dict[str, int]:
    """Sync analytics for all workspaces with active accounts.

    Called by the Celery periodic task.
    """
    from app.domains.control.models import Workspace

    result = await db.execute(
        select(SocialAccount.workspace_id)
        .where(
            SocialAccount.is_active == True,
            SocialAccount.token_status == TokenStatus.VALID,
        )
        .group_by(SocialAccount.workspace_id)
    )
    workspace_ids = [row[0] for row in result.all()]

    total_facts = 0
    total_posts = 0
    workspaces_synced = 0

    for ws_id in workspace_ids:
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as ws_db:
                stats = await sync_analytics_for_workspace(ws_db, ws_id)
                total_facts += stats["facts_written"]
                total_posts += stats["posts_synced"]
                workspaces_synced += 1
        except Exception as exc:
            logger.error(
                "analytics_sync_workspace_failed",
                workspace_id=str(ws_id),
                error=str(exc),
            )

    logger.info(
        "analytics_sync_complete",
        workspaces=workspaces_synced,
        facts=total_facts,
        posts=total_posts,
    )

    return {
        "workspaces_synced": workspaces_synced,
        "facts_written": total_facts,
        "posts_synced": total_posts,
    }
