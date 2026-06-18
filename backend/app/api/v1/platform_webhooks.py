"""Webhook receiver endpoints — inbound platform event processing.

All social platforms deliver events (post metrics, token changes,
content moderation, etc.) to these endpoints. Processing flow:

  1. Receive raw payload
  2. Validate signature (per platform)
  3. Deduplicate via payload hash
  4. Store as WebhookReceipt (received status)
  5. Dispatch to outbox for async processing

Security:
  - Each platform has its own validation method
  - Payload signature is verified before any processing
  - SHA-256 hash of payload used for dedup
  - Raw payload stored for audit trail

Endpoints:
  POST /api/v1/webhooks/{platform}
  GET  /api/v1/webhooks/status/{receipt_id}
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.deps import DbSession
from app.config import get_settings
from app.domains.control.models import (
    WebhookReceipt,
    WebhookProcessingStatus,
    OutboxEvent,
    OutboxStatus,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Supported platforms with their signature header names
_SIGNATURE_HEADERS: dict[str, str] = {
    "instagram": "x-hub-signature-256",
    "youtube": "x-goog-channel-token",
    "twitter": "x-twitter-webhooks-signature",
    "linkedin": "x-li-signature",
    "tiktok": "x-tiktok-signature",
}


def _hash_payload(payload: bytes) -> str:
    """SHA-256 hash of raw payload for deduplication."""
    return hashlib.sha256(payload).hexdigest()


def _extract_event_id(platform: str, payload: dict) -> str | None:
    """Extract platform-specific event ID for deduplication."""
    if platform == "instagram":
        return payload.get("entry", [{}])[0].get("id")
    elif platform == "youtube":
        return payload.get("resourceId", {}).get("videoId")
    elif platform == "twitter":
        return payload.get("tweet_create_events", [{}])[0].get("id_str")
    elif platform == "tiktok":
        return payload.get("event_id")
    return None


def _hmac_sha256_hex(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _hmac_sha256_b64(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _parse_kv_signature(header: str) -> dict[str, str]:
    parts = {}
    for chunk in header.split(","):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            parts[k.strip()] = v.strip()
    return parts


async def _validate_signature(
    platform: str, raw_body: bytes, signature: str | None,
) -> bool:
    """Constant-time HMAC verification of platform webhook signature.

    Returns False when:
      - signature header missing
      - platform secret not configured (refuses unverifiable traffic)
      - signature does not match
    """
    if not signature:
        return False

    settings = get_settings()

    if platform == "instagram":
        secret = settings.INSTAGRAM_APP_SECRET
        if not secret:
            logger.warning("webhook_secret_missing", platform=platform)
            return False
        # Meta sends "sha256=<hex>"
        if not signature.startswith("sha256="):
            return False
        provided = signature.split("=", 1)[1]
        expected = _hmac_sha256_hex(secret, raw_body)
        return hmac.compare_digest(provided, expected)

    if platform == "youtube":
        # YouTube PubSubHubbub uses a per-channel verify token, not HMAC.
        expected = settings.YOUTUBE_WEBHOOK_CHANNEL_TOKEN
        if not expected:
            logger.warning("webhook_secret_missing", platform=platform)
            return False
        return hmac.compare_digest(signature, expected)

    if platform == "twitter":
        secret = settings.TWITTER_API_SECRET
        if not secret:
            logger.warning("webhook_secret_missing", platform=platform)
            return False
        # Twitter sends "sha256=<base64>"
        provided = signature.split("=", 1)[1] if signature.startswith("sha256=") else signature
        expected = _hmac_sha256_b64(secret, raw_body)
        return hmac.compare_digest(provided, expected)

    if platform == "linkedin":
        secret = settings.LINKEDIN_WEBHOOK_SECRET or settings.LINKEDIN_CLIENT_SECRET
        if not secret:
            logger.warning("webhook_secret_missing", platform=platform)
            return False
        expected_hex = _hmac_sha256_hex(secret, raw_body)
        expected_b64 = _hmac_sha256_b64(secret, raw_body)
        return hmac.compare_digest(signature, expected_hex) or hmac.compare_digest(
            signature, expected_b64
        )

    if platform == "tiktok":
        secret = settings.TIKTOK_WEBHOOK_SECRET
        if not secret:
            logger.warning("webhook_secret_missing", platform=platform)
            return False
        # TikTok format: "t=<unix_ts>,s=<hex>"
        parts = _parse_kv_signature(signature)
        ts = parts.get("t")
        provided = parts.get("s")
        if not ts or not provided:
            return False
        signed_body = ts.encode("utf-8") + b"." + raw_body
        expected = _hmac_sha256_hex(secret, signed_body)
        return hmac.compare_digest(provided, expected)

    return False


async def _check_duplicate(
    db, platform: str, event_id: str | None, payload_hash: str,
) -> WebhookReceipt | None:
    """Check if this webhook has already been received."""
    if event_id:
        result = await db.execute(
            select(WebhookReceipt).where(
                WebhookReceipt.provider == platform,
                WebhookReceipt.external_event_id == event_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    result = await db.execute(
        select(WebhookReceipt).where(
            WebhookReceipt.provider == platform,
            WebhookReceipt.payload_hash == payload_hash,
        )
    )
    return result.scalar_one_or_none()


@router.post(
    "/{platform}",
    status_code=200,
    summary="Receive webhook from social platform",
)
async def receive_webhook(
    platform: str,
    request: Request,
    db: DbSession,
) -> JSONResponse:
    """Receive and process inbound webhook from a social platform.

    Validates signature, deduplicates, stores receipt, and queues
    for async processing via the outbox pattern.
    """
    if platform not in _SIGNATURE_HEADERS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported platform: {platform}"},
        )

    raw_body = await request.body()
    payload_hash = _hash_payload(raw_body)

    # Parse payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("webhook_invalid_json", platform=platform)
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON payload"},
        )

    # Extract signature
    sig_header = _SIGNATURE_HEADERS[platform]
    signature = request.headers.get(sig_header)

    # Validate signature
    sig_valid = await _validate_signature(platform, raw_body, signature)

    # Extract event ID for dedup
    event_id = _extract_event_id(platform, payload)

    # Check for duplicates
    duplicate = await _check_duplicate(db, platform, event_id, payload_hash)
    if duplicate:
        logger.info(
            "webhook_duplicate",
            platform=platform,
            receipt_id=str(duplicate.id),
        )
        # Update status to DUPLICATE if not already
        if duplicate.processing_status == WebhookProcessingStatus.RECEIVED:
            duplicate.processing_status = WebhookProcessingStatus.DUPLICATE
            await db.commit()
        return JSONResponse(
            status_code=200,
            content={"status": "duplicate", "receipt_id": str(duplicate.id)},
        )

    # Store receipt
    receipt = WebhookReceipt(
        provider=platform,
        external_event_id=event_id,
        payload_hash=payload_hash,
        signature_valid=sig_valid,
        raw_payload=payload,
        processing_status=(
            WebhookProcessingStatus.VALIDATED
            if sig_valid
            else WebhookProcessingStatus.RECEIVED
        ),
    )
    db.add(receipt)
    await db.flush()

    # If signature valid, queue for async processing via outbox
    if sig_valid:
        outbox_event = OutboxEvent(
            event_type=f"webhook.{platform}.received",
            aggregate_type="webhook_receipt",
            aggregate_id=str(receipt.id),
            payload={
                "platform": platform,
                "receipt_id": str(receipt.id),
                "event_id": event_id,
            },
            status=OutboxStatus.PENDING,
        )
        db.add(outbox_event)

    await db.commit()

    logger.info(
        "webhook_received",
        platform=platform,
        receipt_id=str(receipt.id),
        signature_valid=sig_valid,
    )

    return JSONResponse(
        status_code=200,
        content={"status": "received", "receipt_id": str(receipt.id)},
    )


@router.get(
    "/status/{receipt_id}",
    summary="Get webhook processing status",
)
async def get_webhook_status(
    receipt_id: uuid.UUID,
    db: DbSession,
) -> dict:
    """Check the processing status of a received webhook."""
    result = await db.execute(
        select(WebhookReceipt).where(WebhookReceipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        return JSONResponse(
            status_code=404,
            content={"error": "Webhook receipt not found"},
        )

    return {
        "receipt_id": str(receipt.id),
        "provider": receipt.provider,
        "processing_status": receipt.processing_status.value,
        "signature_valid": receipt.signature_valid,
        "received_at": receipt.received_at.isoformat() if receipt.received_at else None,
        "processed_at": receipt.processed_at.isoformat() if receipt.processed_at else None,
        "error_message": receipt.error_message,
    }


# ── Instagram verification (Meta requires GET challenge) ─────────────────

@router.get(
    "/instagram",
    summary="Instagram webhook verification",
)
async def verify_instagram_webhook(
    hub_mode: str = "",
    hub_challenge: str = "",
    hub_verify_token: str = "",
) -> JSONResponse:
    """Handle Instagram/Meta webhook verification challenge.

    Meta sends a GET request with hub.mode, hub.challenge, and
    hub.verify_token. We must respond with the challenge value.
    """
    from app.config import get_settings
    settings = get_settings()

    expected_token = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("instagram_webhook_verified")
        return JSONResponse(
            status_code=200,
            content=int(hub_challenge) if hub_challenge.isdigit() else hub_challenge,
        )

    logger.warning("instagram_webhook_verify_failed", token=hub_verify_token)
    return JSONResponse(status_code=403, content={"error": "Verification failed"})
