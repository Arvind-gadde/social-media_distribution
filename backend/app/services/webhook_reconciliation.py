"""Reconcile inbound platform webhook payloads back to ContentVariant metrics.

Each platform pushes engagement updates (views, likes, comments, …) on its own
schedule and in its own format. This module converts those payloads into the
canonical ContentVariant counters and emits a ``publish.metrics.updated``
outbox event for downstream consumers (analytics, notifications, goal agent).

Design rules:
  * Counters are monotonic — we never lower a value, even if a webhook delivery
    is delayed and arrives stale.
  * Parsing is best-effort. Unknown payload shapes are recorded as
    ``unmatched`` and do not abort processing.
  * Reconciliation never raises on a missing match; instead it returns a
    ``ReconciliationResult`` so the dispatcher can decide what to do.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import (
    OutboxEvent,
    OutboxStatus,
    WebhookReceipt,
)
from app.domains.execution.models import (
    ContentVariant,
    PublishJob,
    PublishStatus,
)

log = structlog.get_logger(__name__)


# Canonical metric names used internally.
METRIC_FIELDS = ("views", "likes", "comments", "shares", "saves")


@dataclass
class ParsedMetrics:
    platform_post_id: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)


@dataclass
class ReconciliationResult:
    matched: bool = False
    platform_post_id: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)
    variant_id: uuid.UUID | None = None
    publish_job_id: uuid.UUID | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Per-platform payload parsers
# ─────────────────────────────────────────────────────────────────────────────


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_payload(platform: str, payload: dict | None) -> ParsedMetrics:
    """Dispatch to a platform-specific parser. Unknown platforms return empty."""
    if not isinstance(payload, dict):
        return ParsedMetrics()
    parser = _PARSERS.get(platform)
    if parser is None:
        return ParsedMetrics()
    try:
        return parser(payload)
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("webhook_parse_failed", platform=platform, error=str(exc))
        return ParsedMetrics()


def _parse_instagram(payload: dict) -> ParsedMetrics:
    """Instagram Graph webhook: entry[].changes[].value carries metric updates."""
    entries = payload.get("entry") or []
    if not entries:
        return ParsedMetrics()
    first = entries[0] or {}
    changes = first.get("changes") or []
    if not changes:
        return ParsedMetrics(platform_post_id=str(first.get("id") or "") or None)
    value = (changes[0] or {}).get("value") or {}
    metrics: dict[str, int] = {}
    if (views := _coerce_int(value.get("impressions"))) is not None:
        metrics["views"] = views
    elif (reach := _coerce_int(value.get("reach"))) is not None:
        metrics["views"] = reach
    if (likes := _coerce_int(value.get("like_count"))) is not None:
        metrics["likes"] = likes
    if (comments := _coerce_int(value.get("comments_count"))) is not None:
        metrics["comments"] = comments
    if (saves := _coerce_int(value.get("saved"))) is not None:
        metrics["saves"] = saves
    return ParsedMetrics(
        platform_post_id=str(value.get("media_id") or first.get("id") or "") or None,
        metrics=metrics,
    )


def _parse_youtube(payload: dict) -> ParsedMetrics:
    """YouTube webhook notifies of change; metrics fetched lazily by analytics.

    The PubSubHubbub feed only contains the videoId and channelId. We surface
    the post id so the receipt can be tied to the right PublishJob; metric
    refresh is handled by the analytics sync worker.
    """
    resource = payload.get("resourceId") or {}
    video_id = resource.get("videoId") or payload.get("videoId")
    return ParsedMetrics(platform_post_id=str(video_id) if video_id else None)


def _parse_twitter(payload: dict) -> ParsedMetrics:
    """Twitter Account Activity API: tweet_create_events / metrics."""
    events = payload.get("tweet_metrics_events") or payload.get("tweet_create_events") or []
    if not events:
        return ParsedMetrics()
    tweet = events[0] or {}
    metrics_obj = tweet.get("public_metrics") or tweet
    metrics: dict[str, int] = {}
    if (impressions := _coerce_int(metrics_obj.get("impression_count"))) is not None:
        metrics["views"] = impressions
    if (likes := _coerce_int(metrics_obj.get("like_count") or metrics_obj.get("favorite_count"))) is not None:
        metrics["likes"] = likes
    if (replies := _coerce_int(metrics_obj.get("reply_count"))) is not None:
        metrics["comments"] = replies
    if (retweets := _coerce_int(metrics_obj.get("retweet_count"))) is not None:
        metrics["shares"] = retweets
    return ParsedMetrics(
        platform_post_id=str(tweet.get("id_str") or tweet.get("id") or "") or None,
        metrics=metrics,
    )


def _parse_linkedin(payload: dict) -> ParsedMetrics:
    """LinkedIn ugcPost activity webhook."""
    activity = payload.get("activity") or payload
    urn = activity.get("ugcPostUrn") or activity.get("urn") or activity.get("activity")
    stats = activity.get("totalShareStatistics") or activity.get("stats") or {}
    metrics: dict[str, int] = {}
    if (likes := _coerce_int(stats.get("likeCount"))) is not None:
        metrics["likes"] = likes
    if (comments := _coerce_int(stats.get("commentCount"))) is not None:
        metrics["comments"] = comments
    if (shares := _coerce_int(stats.get("shareCount"))) is not None:
        metrics["shares"] = shares
    if (impressions := _coerce_int(stats.get("impressionCount"))) is not None:
        metrics["views"] = impressions
    return ParsedMetrics(
        platform_post_id=str(urn) if urn else None,
        metrics=metrics,
    )


def _parse_tiktok(payload: dict) -> ParsedMetrics:
    """TikTok webhook content data block."""
    data = payload.get("data") or payload
    metrics_obj = data.get("metrics") or data.get("stats") or {}
    metrics: dict[str, int] = {}
    if (views := _coerce_int(metrics_obj.get("view_count") or data.get("view_count"))) is not None:
        metrics["views"] = views
    if (likes := _coerce_int(metrics_obj.get("like_count") or data.get("like_count"))) is not None:
        metrics["likes"] = likes
    if (comments := _coerce_int(metrics_obj.get("comment_count") or data.get("comment_count"))) is not None:
        metrics["comments"] = comments
    if (shares := _coerce_int(metrics_obj.get("share_count") or data.get("share_count"))) is not None:
        metrics["shares"] = shares
    return ParsedMetrics(
        platform_post_id=str(data.get("publish_id") or data.get("video_id") or "") or None,
        metrics=metrics,
    )


_PARSERS = {
    "instagram": _parse_instagram,
    "youtube": _parse_youtube,
    "twitter": _parse_twitter,
    "linkedin": _parse_linkedin,
    "tiktok": _parse_tiktok,
}


# ─────────────────────────────────────────────────────────────────────────────
# Reconciliation
# ─────────────────────────────────────────────────────────────────────────────


async def reconcile_receipt(
    db: AsyncSession,
    receipt: WebhookReceipt,
) -> ReconciliationResult:
    """Apply a stored webhook receipt's metrics to its ContentVariant."""
    parsed = parse_payload(receipt.provider, receipt.raw_payload)
    result = ReconciliationResult(
        platform_post_id=parsed.platform_post_id,
        metrics=parsed.metrics,
    )

    if not parsed.platform_post_id:
        log.info(
            "webhook_reconcile_no_post_id",
            receipt_id=str(receipt.id),
            platform=receipt.provider,
        )
        return result

    job_result = await db.execute(
        select(PublishJob).where(
            PublishJob.target_platform == receipt.provider,
            PublishJob.platform_post_id == parsed.platform_post_id,
        )
    )
    job = job_result.scalar_one_or_none()
    if job is None:
        log.info(
            "webhook_reconcile_no_match",
            receipt_id=str(receipt.id),
            platform=receipt.provider,
            platform_post_id=parsed.platform_post_id,
        )
        return result

    result.matched = True
    result.publish_job_id = job.id
    result.variant_id = job.content_variant_id

    if not parsed.metrics:
        # Notification-only payload (e.g. YouTube push): nothing to merge.
        await _emit_metrics_event(db, job, parsed.metrics, parsed.platform_post_id)
        return result

    variant_result = await db.execute(
        select(ContentVariant).where(ContentVariant.id == job.content_variant_id)
    )
    variant = variant_result.scalar_one_or_none()
    if variant is None:
        return result

    monotonic = {
        "views": max(variant.total_views, parsed.metrics.get("views", 0)),
        "likes": max(variant.total_likes, parsed.metrics.get("likes", 0)),
        "comments": max(variant.total_comments, parsed.metrics.get("comments", 0)),
        "shares": max(variant.total_shares, parsed.metrics.get("shares", 0)),
        "saves": max(variant.total_saves, parsed.metrics.get("saves", 0)),
    }
    engagement_rate = _engagement_rate(monotonic)
    await db.execute(
        update(ContentVariant)
        .where(ContentVariant.id == variant.id)
        .values(
            total_views=monotonic["views"],
            total_likes=monotonic["likes"],
            total_comments=monotonic["comments"],
            total_shares=monotonic["shares"],
            total_saves=monotonic["saves"],
            engagement_rate=engagement_rate,
            updated_at=datetime.now(timezone.utc),
        )
    )

    # Mark the publish job as completed if reconciliation confirms it is live.
    if job.status not in (PublishStatus.COMPLETED, PublishStatus.DEAD_LETTER):
        await db.execute(
            update(PublishJob)
            .where(PublishJob.id == job.id)
            .values(status=PublishStatus.COMPLETED)
        )

    await _emit_metrics_event(db, job, monotonic, parsed.platform_post_id)
    return result


def _engagement_rate(metrics: dict[str, int]) -> float:
    views = max(metrics.get("views", 0), 1)
    interactions = (
        metrics.get("likes", 0)
        + metrics.get("comments", 0)
        + metrics.get("shares", 0)
        + metrics.get("saves", 0)
    )
    return round(interactions / views, 4)


async def _emit_metrics_event(
    db: AsyncSession,
    job: PublishJob,
    metrics: dict[str, int],
    platform_post_id: str,
) -> None:
    db.add(
        OutboxEvent(
            workspace_id=job.workspace_id,
            event_type="publish.metrics.updated",
            aggregate_type="publish_job",
            aggregate_id=str(job.id),
            payload={
                "platform": job.target_platform,
                "platform_post_id": platform_post_id,
                "metrics": metrics,
            },
            status=OutboxStatus.PENDING,
        )
    )
