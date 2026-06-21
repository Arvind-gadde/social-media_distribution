"""Publish job executor — processes queued publish jobs through platform adapters.

Responsibilities:
  - Lease pending jobs (concurrency-safe via lease_owner)
  - Decrypt social account tokens
  - Transform ContentVariant → PublishPayload
  - Call platform adapter
  - Record PublishAttempt (immutable)
  - Update PublishJob status + retry logic
  - Emit outbox events on success/failure

Called by Celery task: process_publish_jobs (every 5 min).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domains.control.models import (
    SocialAccount, TokenStatus, OutboxEvent, OutboxStatus,
)
from app.domains.execution.models import (
    PublishJob, PublishStatus, PublishAttempt,
    ContentAsset, ContentVariant,
)
from app.integrations.platforms.adapters import (
    PublishPayload, PublishResult, get_adapter,
)

logger = structlog.get_logger(__name__)

# Lease duration — if a worker crashes, the job becomes available again
LEASE_DURATION = timedelta(minutes=10)
BATCH_SIZE = 20


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def process_due_jobs(
    db: AsyncSession,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Process all due publish jobs.

    Leases jobs, publishes them, records attempts, and updates status.

    Args:
        db: Database session
        worker_id: Unique identifier for this worker instance

    Returns:
        Summary dict with counts of processed, succeeded, failed jobs.
    """
    lease_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
    now = _utcnow()

    # Find and lease due jobs
    result = await db.execute(
        select(PublishJob)
        .where(
            PublishJob.status.in_([
                PublishStatus.QUEUED,
                PublishStatus.RETRYABLE_FAILED,
            ]),
            PublishJob.scheduled_at <= now,
            # Not currently leased by another worker
            (
                (PublishJob.lease_owner.is_(None))
                | (PublishJob.last_lease_at < now - LEASE_DURATION)
            ),
        )
        .order_by(PublishJob.scheduled_at.asc())
        .limit(BATCH_SIZE)
    )
    jobs = result.scalars().all()

    if not jobs:
        return {"processed": 0, "succeeded": 0, "failed": 0}

    # Lease the jobs
    job_ids = [job.id for job in jobs]
    await db.execute(
        update(PublishJob)
        .where(PublishJob.id.in_(job_ids))
        .values(
            lease_owner=lease_id,
            last_lease_at=now,
            status=PublishStatus.LEASED,
        )
    )
    await db.commit()

    succeeded = 0
    failed = 0

    for job in jobs:
        try:
            success = await _execute_single_job(db, job, lease_id)
            if success:
                succeeded += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error(
                "publish_job_crash",
                job_id=str(job.id),
                error=str(exc),
            )
            # Mark as retryable if under max retries
            await _mark_job_failed(db, job, str(exc), retryable=True)
            failed += 1

    logger.info(
        "publish_batch_complete",
        processed=len(jobs),
        succeeded=succeeded,
        failed=failed,
    )

    return {
        "processed": len(jobs),
        "succeeded": succeeded,
        "failed": failed,
    }


async def _execute_single_job(
    db: AsyncSession,
    job: PublishJob,
    lease_id: str,
) -> bool:
    """Execute a single publish job.

    Returns True if published successfully, False otherwise.
    """
    # Idempotency: if this job has already been published (lease re-acquired
    # after a crash that wrote the post but not the COMPLETED status), do not
    # publish again — close it out instead.
    if job.platform_post_id:
        logger.info(
            "publish_job_idempotent_skip",
            job_id=str(job.id),
            existing_post_id=job.platform_post_id,
        )
        await db.execute(
            update(PublishJob)
            .where(PublishJob.id == job.id)
            .values(
                status=PublishStatus.COMPLETED,
                completed_at=job.completed_at or _utcnow(),
                lease_owner=None,
            )
        )
        await db.commit()
        return True

    # Pre-flight: any prior successful attempt? Treat as completed.
    prior = await _find_successful_prior_attempt(db, job.id)
    if prior is not None:
        logger.info(
            "publish_job_prior_success_detected",
            job_id=str(job.id),
            prior_request_id=prior.provider_request_id,
        )
        await db.execute(
            update(PublishJob)
            .where(PublishJob.id == job.id)
            .values(
                status=PublishStatus.COMPLETED,
                platform_post_id=(prior.provider_response or {}).get("post_id")
                or prior.provider_request_id,
                completed_at=_utcnow(),
                lease_owner=None,
            )
        )
        await db.commit()
        return True

    # Update status to RUNNING
    await db.execute(
        update(PublishJob)
        .where(PublishJob.id == job.id)
        .values(status=PublishStatus.RUNNING)
    )
    await db.flush()

    # Load the content variant
    variant_result = await db.execute(
        select(ContentVariant).where(ContentVariant.id == job.content_variant_id)
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        await _mark_job_failed(db, job, "Content variant not found", retryable=False)
        return False

    # Load the social account
    account_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == job.social_account_id,
            SocialAccount.workspace_id == job.workspace_id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        await _mark_job_failed(db, job, "Social account not found", retryable=False)
        return False

    if not account.is_active:
        await _mark_job_failed(db, job, "Social account is inactive", retryable=False)
        return False

    if account.token_status != TokenStatus.VALID:
        await _mark_job_failed(
            db,
            job,
            f"Social account token is {account.token_status.value}",
            retryable=False,
        )
        return False

    if account.platform != job.target_platform:
        await _mark_job_failed(
            db,
            job,
            "Publish job platform does not match social account platform",
            retryable=False,
        )
        return False

    # Decrypt token
    access_token = _decrypt_token(account.encrypted_access_token, job.workspace_id)
    if not access_token:
        await _mark_job_failed(db, job, "Token decryption failed", retryable=False)
        return False

    # Build payload from variant
    payload = await _variant_to_payload(db, variant)
    payload_error = _validate_payload_for_platform(job.target_platform, payload)
    if payload_error:
        await _mark_job_failed(db, job, payload_error, retryable=False)
        return False

    # Get adapter
    try:
        adapter = get_adapter(
            platform=job.target_platform,
            access_token=access_token,
            platform_user_id=account.platform_user_id,
            platform_username=account.platform_username,
            base_url=account.platform_url,
        )
    except ValueError as exc:
        await _mark_job_failed(db, job, str(exc), retryable=False)
        return False

    # Publish — refresh-and-retry once on auth failure
    result = await adapter.publish(payload)

    if _is_auth_failure(result):
        refreshed = await _try_refresh_token(db, adapter, account, job.workspace_id)
        if refreshed:
            logger.info(
                "publish_token_refreshed_retry",
                job_id=str(job.id),
                platform=job.target_platform,
            )
            # Rebuild the adapter so it picks up the new token.
            try:
                adapter = get_adapter(
                    platform=job.target_platform,
                    access_token=refreshed,
                    platform_user_id=account.platform_user_id,
                    platform_username=account.platform_username,
                    base_url=account.platform_url,
                )
            except ValueError as exc:
                await _mark_job_failed(db, job, str(exc), retryable=False)
                return False
            result = await adapter.publish(payload)

    # Record attempt
    attempt = PublishAttempt(
        publish_job_id=job.id,
        attempt_number=job.retry_count + 1,
        provider_response_code=result.provider_response_code,
        provider_request_id=result.provider_request_id,
        provider_response=result.provider_response,
        failure_class=result.failure_class,
        retryable=result.retryable,
        payload_snapshot={
            "caption_length": len(payload.caption),
            "hashtag_count": len(payload.hashtags),
            "media_type": payload.media_type,
        },
        latency_ms=result.latency_ms,
    )
    db.add(attempt)

    # Audit every publish attempt — this is the point a decrypted platform token
    # is used, so it belongs in the append-only trail. Flushed here; committed by
    # the success branch or _mark_job_failed below.
    from app.services.audit_service import audit_publish_attempt
    await audit_publish_attempt(
        db,
        workspace_id=job.workspace_id,
        publish_job_id=job.id,
        actor_id="system",
        platform=job.target_platform,
        status="success" if result.success else "failed",
    )

    if result.success:
        await db.execute(
            update(PublishJob)
            .where(PublishJob.id == job.id)
            .values(
                status=PublishStatus.COMPLETED,
                platform_post_id=result.platform_post_id,
                platform_post_url=result.platform_post_url,
                completed_at=_utcnow(),
                lease_owner=None,
            )
        )

        # Emit success event
        outbox = OutboxEvent(
            workspace_id=job.workspace_id,
            event_type="publish.completed",
            aggregate_type="publish_job",
            aggregate_id=str(job.id),
            payload={
                "platform": job.target_platform,
                "post_id": result.platform_post_id,
                "post_url": result.platform_post_url,
            },
            status=OutboxStatus.PENDING,
        )
        db.add(outbox)
        await db.commit()

        logger.info(
            "publish_success",
            job_id=str(job.id),
            platform=job.target_platform,
            post_id=result.platform_post_id,
        )
        return True
    else:
        await _mark_job_failed(
            db, job, result.error_message or "Unknown error",
            retryable=result.retryable,
        )
        return False


async def _mark_job_failed(
    db: AsyncSession,
    job: PublishJob,
    error: str,
    *,
    retryable: bool = True,
) -> None:
    """Mark a job as failed with retry logic."""
    new_retry = job.retry_count + 1

    if retryable and new_retry < job.max_retries:
        status = PublishStatus.RETRYABLE_FAILED
    elif retryable and new_retry >= job.max_retries:
        status = PublishStatus.DEAD_LETTER
    else:
        status = PublishStatus.FAILED

    await db.execute(
        update(PublishJob)
        .where(PublishJob.id == job.id)
        .values(
            status=status,
            retry_count=new_retry,
            error_message=error,
            lease_owner=None,
        )
    )

    # Emit failure event for dead-lettered jobs
    if status == PublishStatus.DEAD_LETTER:
        outbox = OutboxEvent(
            workspace_id=job.workspace_id,
            event_type="publish.dead_letter",
            aggregate_type="publish_job",
            aggregate_id=str(job.id),
            payload={
                "platform": job.target_platform,
                "error": error,
                "retries_exhausted": new_retry,
            },
            status=OutboxStatus.PENDING,
        )
        db.add(outbox)

    await db.commit()

    logger.warning(
        "publish_failed",
        job_id=str(job.id),
        status=status.value,
        retry=new_retry,
        error=error,
    )


def _decrypt_token(encrypted: str | None, workspace_id: uuid.UUID) -> str | None:
    """Decrypt an encrypted access token using TokenVault.

    Args:
        encrypted: Encrypted token string
        workspace_id: Workspace UUID for key derivation

    Returns:
        Decrypted plaintext token or None
    """
    if not encrypted:
        return None
    
    from app.services.token_vault import get_vault
    
    try:
        vault = get_vault()
        return vault.decrypt(encrypted, workspace_id)
    except Exception as exc:
        logger.error(
            "token_decryption_failed",
            workspace_id=str(workspace_id),
            error=str(exc),
        )
        return None


async def _variant_to_payload(
    db: AsyncSession,
    variant: ContentVariant,
) -> PublishPayload:
    """Transform a ContentVariant into a platform-agnostic PublishPayload."""
    asset_result = await db.execute(
        select(ContentAsset)
        .where(
            ContentAsset.workspace_id == variant.workspace_id,
            ContentAsset.project_id == variant.project_id,
        )
        .order_by(ContentAsset.created_at.asc())
    )
    assets = list(asset_result.scalars().all())
    media_urls = [_asset_public_url(asset) for asset in assets]
    media_urls = [url for url in media_urls if url]
    media_type = _infer_media_type(assets)

    return PublishPayload(
        caption=variant.caption or "",
        hashtags=variant.hashtags or [],
        media_urls=media_urls,
        media_type=media_type,
        thread_tweets=variant.thread_tweets or [],
        script_outline=variant.script_outline or "",
    )


def _asset_public_url(asset: ContentAsset) -> str:
    """Return a public URL for a stored asset when configured."""
    settings = get_settings()
    if not settings.S3_PUBLIC_BASE_URL:
        return ""
    return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{asset.storage_key}"


def _infer_media_type(assets: list[ContentAsset]) -> str:
    """Infer platform payload media type from project assets."""
    if not assets:
        return "text"
    if len(assets) > 1:
        return "carousel"
    media_kind = (assets[0].media_kind or "").lower()
    if media_kind in {"image", "video"}:
        return media_kind
    return "text"


async def _find_successful_prior_attempt(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> PublishAttempt | None:
    """Return the most recent attempt for this job whose provider call succeeded.

    Used as an idempotency guard so a lease re-acquired after a partial commit
    does not republish content the platform already accepted.
    """
    result = await db.execute(
        select(PublishAttempt)
        .where(
            PublishAttempt.publish_job_id == job_id,
            PublishAttempt.provider_response_code.in_([200, 201, 202, 204]),
        )
        .order_by(PublishAttempt.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _is_auth_failure(result: PublishResult) -> bool:
    """Heuristic: did this publish fail because the access token was rejected?"""
    if result.success:
        return False
    if result.provider_response_code == 401:
        return True
    failure = (result.failure_class or "").lower()
    return failure in {"auth", "unauthorized", "token_expired", "token_invalid"}


async def _try_refresh_token(
    db: AsyncSession,
    adapter,
    account: SocialAccount,
    workspace_id: uuid.UUID,
) -> str | None:
    """Refresh the account's access token via the platform adapter.

    Returns the new access token on success, None when the refresh is
    impossible (no refresh token, adapter does not implement refresh, etc.).
    """
    refresh_plain = _decrypt_token(account.encrypted_refresh_token, workspace_id)
    if not refresh_plain:
        return None

    try:
        new_tokens = await adapter.refresh_token(refresh_plain)
    except NotImplementedError:
        return None
    except Exception as exc:
        logger.warning(
            "publish_token_refresh_failed",
            account_id=str(account.id),
            error=str(exc),
        )
        return None

    if not isinstance(new_tokens, dict):
        return None

    new_access = new_tokens.get("access_token") or new_tokens.get("accessToken")
    if not new_access:
        return None

    from app.services.token_vault import get_vault

    vault = get_vault()
    try:
        encrypted_access = vault.encrypt(new_access, workspace_id)
    except Exception as exc:
        logger.error(
            "publish_token_reencrypt_failed",
            account_id=str(account.id),
            error=str(exc),
        )
        return None

    update_values: dict[str, Any] = {
        "encrypted_access_token": encrypted_access,
        "token_status": TokenStatus.VALID,
    }

    new_refresh = new_tokens.get("refresh_token") or new_tokens.get("refreshToken")
    if new_refresh:
        try:
            update_values["encrypted_refresh_token"] = vault.encrypt(
                new_refresh, workspace_id
            )
        except Exception:
            pass

    expires_in = new_tokens.get("expires_in") or new_tokens.get("expiresIn")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        update_values["token_expires_at"] = _utcnow() + timedelta(seconds=int(expires_in))

    from app.domains.control.models import SocialAccount as _SA

    await db.execute(
        update(_SA).where(_SA.id == account.id).values(**update_values)
    )
    await db.flush()

    return new_access


def _validate_payload_for_platform(
    platform: str,
    payload: PublishPayload,
) -> str | None:
    """Return an actionable validation error when a platform cannot publish."""
    if platform == "instagram" and payload.media_type not in {"image", "video"}:
        return "Instagram publishing requires exactly one image or video asset"
    if platform == "youtube" and payload.media_type != "video":
        return "YouTube publishing requires a video asset"
    if platform == "tiktok" and payload.media_type != "video":
        return "TikTok publishing requires a video asset"
    if platform == "pinterest" and payload.media_type not in {"image", "video"}:
        return "Pinterest publishing requires an image or video pin"
    if payload.media_type == "carousel":
        return f"{platform} carousel publishing is not implemented yet"
    if not (payload.caption or payload.media_urls or payload.thread_tweets):
        return "Publish payload is empty"
    return None
