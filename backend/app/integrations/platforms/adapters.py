"""Platform publishing adapters — abstract base + per-platform implementations.

Each adapter handles:
  - Credential decryption and token refresh
  - Rate limit awareness
  - Content format transformation (variant → platform-native payload)
  - Actual API call with error classification
  - Response parsing into PublishAttempt data

All adapters return a standardized PublishResult.
"""
from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class PublishPayload:
    """Standardized content payload for publishing."""
    caption: str
    hashtags: list[str] = field(default_factory=list)
    media_urls: list[str] = field(default_factory=list)
    media_type: str = "text"  # text, image, video, carousel
    thread_tweets: list[str] = field(default_factory=list)
    script_outline: str = ""
    link_url: str = ""
    schedule_at: datetime | None = None


@dataclass
class PublishResult:
    """Standardized result from a publish attempt."""
    success: bool
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    provider_response_code: int | None = None
    provider_request_id: str | None = None
    provider_response: dict | None = None
    failure_class: str | None = None
    retryable: bool = False
    error_message: str | None = None
    latency_ms: int = 0


class PlatformAdapter(abc.ABC):
    """Abstract base class for platform publishing adapters."""

    PLATFORM: str = ""
    MAX_CAPTION_LENGTH: int = 2200
    MAX_HASHTAGS: int = 30
    SUPPORTED_MEDIA: list[str] = ["text", "image", "video"]

    def __init__(self, access_token: str, **kwargs: Any) -> None:
        self._access_token = access_token
        self._extra = kwargs

    @abc.abstractmethod
    async def publish(self, payload: PublishPayload) -> PublishResult:
        """Publish content to the platform. Must be implemented per platform."""
        ...

    @abc.abstractmethod
    async def validate_token(self) -> bool:
        """Check if the access token is still valid."""
        ...

    @abc.abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token. Returns new token dict."""
        ...

    def _truncate_caption(self, caption: str) -> str:
        """Truncate caption to platform limit."""
        if len(caption) <= self.MAX_CAPTION_LENGTH:
            return caption
        return caption[: self.MAX_CAPTION_LENGTH - 3] + "..."

    def _format_hashtags(self, hashtags: list[str], max_count: int | None = None) -> str:
        """Format hashtags for appending to caption."""
        limit = max_count or self.MAX_HASHTAGS
        clean = [
            f"#{tag.lstrip('#')}" for tag in hashtags[:limit] if tag.strip()
        ]
        return " ".join(clean)

    def _build_full_caption(self, payload: PublishPayload) -> str:
        """Combine caption + hashtags into full post text."""
        caption = payload.caption
        if payload.hashtags:
            hashtag_str = self._format_hashtags(payload.hashtags)
            full = f"{caption}\n\n{hashtag_str}"
            return self._truncate_caption(full)
        return self._truncate_caption(caption)


# ─── Instagram ────────────────────────────────────────────────────────────────


class InstagramAdapter(PlatformAdapter):
    """Instagram Graph API adapter for business/creator accounts.

    Endpoints:
      - POST /{ig-user-id}/media (create container)
      - POST /{ig-user-id}/media_publish (publish container)
      - GET /{ig-user-id} (validate token)

    Requires: Instagram Business Account + Facebook Page + Graph API token
    """

    PLATFORM = "instagram"
    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30
    API_BASE = "https://graph.facebook.com/v19.0"

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        try:
            import httpx

            ig_user_id = self._extra.get("platform_user_id", "")
            caption = self._build_full_caption(payload)

            # Step 1: Create media container
            container_params: dict[str, Any] = {
                "caption": caption,
                "access_token": self._access_token,
            }

            if payload.media_type == "image" and payload.media_urls:
                container_params["image_url"] = payload.media_urls[0]
            elif payload.media_type == "video" and payload.media_urls:
                container_params["video_url"] = payload.media_urls[0]
                container_params["media_type"] = "REELS"

            async with httpx.AsyncClient(timeout=60) as client:
                # Create container
                resp = await client.post(
                    f"{self.API_BASE}/{ig_user_id}/media",
                    data=container_params,
                )
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code != 200:
                    return PublishResult(
                        success=False,
                        provider_response_code=resp.status_code,
                        provider_response=resp.json(),
                        failure_class="container_creation_failed",
                        retryable=resp.status_code >= 500,
                        error_message=resp.text,
                        latency_ms=latency,
                    )

                container_id = resp.json().get("id")

                # Step 2: Publish container
                pub_resp = await client.post(
                    f"{self.API_BASE}/{ig_user_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": self._access_token,
                    },
                )
                latency = int((time.monotonic() - start) * 1000)

                if pub_resp.status_code == 200:
                    post_id = pub_resp.json().get("id", "")
                    return PublishResult(
                        success=True,
                        platform_post_id=post_id,
                        platform_post_url=f"https://www.instagram.com/p/{post_id}/",
                        provider_response_code=200,
                        provider_response=pub_resp.json(),
                        latency_ms=latency,
                    )
                else:
                    return PublishResult(
                        success=False,
                        provider_response_code=pub_resp.status_code,
                        provider_response=pub_resp.json(),
                        failure_class="publish_failed",
                        retryable=pub_resp.status_code >= 500,
                        error_message=pub_resp.text,
                        latency_ms=latency,
                    )

        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/me",
                    params={"access_token": self._access_token},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self._extra.get("app_id", ""),
                        "client_secret": self._extra.get("app_secret", ""),
                        "fb_exchange_token": self._access_token,
                    },
                )
                return resp.json()
        except Exception as exc:
            return {"error": str(exc)}


# ─── Twitter/X ────────────────────────────────────────────────────────────────


class TwitterAdapter(PlatformAdapter):
    """Twitter/X API v2 adapter.

    Endpoints:
      - POST /2/tweets (create tweet)
      - GET /2/users/me (validate token)
    """

    PLATFORM = "twitter"
    MAX_CAPTION_LENGTH = 280
    MAX_HASHTAGS = 5
    API_BASE = "https://api.twitter.com"

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        try:
            import httpx

            # Handle thread vs single tweet
            if payload.thread_tweets and len(payload.thread_tweets) > 1:
                return await self._publish_thread(payload, start)

            caption = self._build_full_caption(payload)
            tweet_data: dict[str, Any] = {"text": caption}

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.API_BASE}/2/tweets",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=tweet_data,
                )
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code in (200, 201):
                    data = resp.json().get("data", {})
                    tweet_id = data.get("id", "")
                    username = self._extra.get("platform_username", "")
                    return PublishResult(
                        success=True,
                        platform_post_id=tweet_id,
                        platform_post_url=f"https://x.com/{username}/status/{tweet_id}",
                        provider_response_code=resp.status_code,
                        provider_response=resp.json(),
                        latency_ms=latency,
                    )
                else:
                    return PublishResult(
                        success=False,
                        provider_response_code=resp.status_code,
                        provider_response=resp.json(),
                        failure_class="tweet_failed",
                        retryable=resp.status_code == 429 or resp.status_code >= 500,
                        error_message=resp.text,
                        latency_ms=latency,
                    )
        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def _publish_thread(
        self, payload: PublishPayload, start: float,
    ) -> PublishResult:
        """Publish a tweet thread."""
        import httpx

        reply_to: str | None = None
        first_tweet_id: str | None = None

        async with httpx.AsyncClient(timeout=30) as client:
            for i, tweet_text in enumerate(payload.thread_tweets):
                tweet_data: dict[str, Any] = {"text": tweet_text}
                if reply_to:
                    tweet_data["reply"] = {"in_reply_to_tweet_id": reply_to}

                resp = await client.post(
                    f"{self.API_BASE}/2/tweets",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=tweet_data,
                )

                if resp.status_code not in (200, 201):
                    return PublishResult(
                        success=False,
                        provider_response_code=resp.status_code,
                        failure_class=f"thread_failed_at_tweet_{i + 1}",
                        retryable=resp.status_code >= 500,
                        error_message=resp.text,
                        latency_ms=int((time.monotonic() - start) * 1000),
                    )

                tweet_id = resp.json().get("data", {}).get("id", "")
                reply_to = tweet_id
                if i == 0:
                    first_tweet_id = tweet_id

        username = self._extra.get("platform_username", "")
        return PublishResult(
            success=True,
            platform_post_id=first_tweet_id,
            platform_post_url=f"https://x.com/{username}/status/{first_tweet_id}",
            provider_response_code=200,
            latency_ms=int((time.monotonic() - start) * 1000),
        )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/2/users/me",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.API_BASE}/2/oauth2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._extra.get("client_id", ""),
                    },
                )
                return resp.json()
        except Exception as exc:
            return {"error": str(exc)}


# ─── LinkedIn ─────────────────────────────────────────────────────────────────


class LinkedInAdapter(PlatformAdapter):
    """LinkedIn API adapter for organization/personal posting."""

    PLATFORM = "linkedin"
    MAX_CAPTION_LENGTH = 3000
    MAX_HASHTAGS = 10
    API_BASE = "https://api.linkedin.com/v2"

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        try:
            import httpx

            author_urn = self._extra.get("author_urn", "")
            caption = self._build_full_caption(payload)

            post_data: dict[str, Any] = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.API_BASE}/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=post_data,
                )
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code == 201:
                    post_id = resp.headers.get("x-restli-id", "")
                    return PublishResult(
                        success=True,
                        platform_post_id=post_id,
                        platform_post_url=f"https://www.linkedin.com/feed/update/{post_id}/",
                        provider_response_code=201,
                        provider_response={"id": post_id},
                        latency_ms=latency,
                    )
                else:
                    return PublishResult(
                        success=False,
                        provider_response_code=resp.status_code,
                        provider_response=resp.json() if resp.text else {},
                        failure_class="linkedin_publish_failed",
                        retryable=resp.status_code >= 500,
                        error_message=resp.text,
                        latency_ms=latency,
                    )
        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/me",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._extra.get("client_id", ""),
                        "client_secret": self._extra.get("client_secret", ""),
                    },
                )
                return resp.json()
        except Exception as exc:
            return {"error": str(exc)}


# ─── YouTube ──────────────────────────────────────────────────────────────────


class YouTubeAdapter(PlatformAdapter):
    """YouTube Data API v3 adapter for Shorts/video publishing."""

    PLATFORM = "youtube"
    MAX_CAPTION_LENGTH = 5000
    MAX_HASHTAGS = 15
    API_BASE = "https://www.googleapis.com/youtube/v3"

    UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3/videos"
    DEFAULT_PRIVACY = "public"
    DEFAULT_CATEGORY_ID = "22"  # People & Blogs

    async def publish(self, payload: PublishPayload) -> PublishResult:
        """Publish a video via YouTube Data API v3 resumable upload.

        Flow (https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol):
          1. Download the source media (already public on R2 / a signed URL).
          2. POST to /upload/youtube/v3/videos?uploadType=resumable with the
             snippet+status JSON and `X-Upload-Content-*` headers. The
             response's Location header is the upload session URL.
          3. PUT the raw video bytes to that URL. A 200/201 response carries
             the new video resource (with id).
        """
        start = time.monotonic()
        latency = lambda: int((time.monotonic() - start) * 1000)

        if payload.media_type != "video":
            return PublishResult(
                success=False,
                failure_class="invalid_media",
                retryable=False,
                error_message="YouTube publishing requires a video asset",
                latency_ms=latency(),
            )
        if not payload.media_urls:
            return PublishResult(
                success=False,
                failure_class="no_video_provided",
                retryable=False,
                error_message="YouTube requires a video file",
                latency_ms=latency(),
            )

        try:
            import httpx

            caption = self._build_full_caption(payload)
            tags = [tag.lstrip("#") for tag in payload.hashtags[: self.MAX_HASHTAGS]]
            video_metadata = {
                "snippet": {
                    "title": (payload.caption or "New Video")[:100],
                    "description": caption,
                    "tags": tags,
                    "categoryId": self._extra.get(
                        "category_id", self.DEFAULT_CATEGORY_ID
                    ),
                },
                "status": {
                    "privacyStatus": self._extra.get(
                        "privacy_status", self.DEFAULT_PRIVACY
                    ),
                    "selfDeclaredMadeForKids": False,
                },
            }

            video_url = payload.media_urls[0]
            content_type = self._extra.get("video_content_type", "video/*")

            async with httpx.AsyncClient(timeout=120) as client:
                # Step 1 — download source bytes.
                source = await client.get(video_url)
                if source.status_code >= 400:
                    return PublishResult(
                        success=False,
                        provider_response_code=source.status_code,
                        failure_class="source_fetch_failed",
                        retryable=source.status_code >= 500,
                        error_message=f"Could not fetch source video ({source.status_code})",
                        latency_ms=latency(),
                    )
                video_bytes = source.content
                if not video_bytes:
                    return PublishResult(
                        success=False,
                        failure_class="empty_video",
                        retryable=False,
                        error_message="Source video has zero bytes",
                        latency_ms=latency(),
                    )
                resolved_type = source.headers.get("content-type") or content_type

                # Step 2 — initiate resumable session.
                init = await client.post(
                    self.UPLOAD_BASE,
                    params={
                        "uploadType": "resumable",
                        "part": "snippet,status",
                    },
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Length": str(len(video_bytes)),
                        "X-Upload-Content-Type": resolved_type,
                    },
                    json=video_metadata,
                )
                if init.status_code not in (200, 201):
                    return PublishResult(
                        success=False,
                        provider_response_code=init.status_code,
                        failure_class=_classify_youtube_error(init.status_code),
                        retryable=init.status_code >= 500 or init.status_code == 429,
                        error_message=f"Resumable session init failed: {init.text[:500]}",
                        provider_response=_safe_json(init),
                        latency_ms=latency(),
                    )

                upload_url = init.headers.get("location") or init.headers.get("Location")
                if not upload_url:
                    return PublishResult(
                        success=False,
                        provider_response_code=init.status_code,
                        failure_class="missing_upload_url",
                        retryable=True,
                        error_message="YouTube did not return a resumable session URL",
                        provider_response=_safe_json(init),
                        latency_ms=latency(),
                    )

                # Step 3 — push the bytes.
                upload = await client.put(
                    upload_url,
                    content=video_bytes,
                    headers={
                        "Content-Type": resolved_type,
                        "Content-Length": str(len(video_bytes)),
                    },
                )

            if upload.status_code in (200, 201):
                video = _safe_json(upload) or {}
                video_id = video.get("id")
                if not video_id:
                    return PublishResult(
                        success=False,
                        provider_response_code=upload.status_code,
                        failure_class="missing_video_id",
                        retryable=True,
                        error_message="Upload succeeded but no video id returned",
                        provider_response=video,
                        latency_ms=latency(),
                    )
                return PublishResult(
                    success=True,
                    platform_post_id=video_id,
                    platform_post_url=f"https://www.youtube.com/watch?v={video_id}",
                    provider_response_code=upload.status_code,
                    provider_response=video,
                    latency_ms=latency(),
                )

            return PublishResult(
                success=False,
                provider_response_code=upload.status_code,
                failure_class=_classify_youtube_error(upload.status_code),
                retryable=upload.status_code >= 500 or upload.status_code == 429,
                error_message=f"Upload failed: {upload.text[:500]}",
                provider_response=_safe_json(upload),
                latency_ms=latency(),
            )

        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=latency(),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/channels",
                    params={"part": "id", "mine": "true"},
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._extra.get("client_id", ""),
                        "client_secret": self._extra.get("client_secret", ""),
                    },
                )
                return resp.json()
        except Exception as exc:
            return {"error": str(exc)}


# ─── TikTok ───────────────────────────────────────────────────────────────────


class TikTokAdapter(PlatformAdapter):
    """TikTok Content Posting API adapter (PULL_FROM_URL flow).

    Uses TikTok's direct-post endpoint to ingest a hosted video URL and
    publish it to the authenticated creator's account.

    Docs: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/
    """

    PLATFORM = "tiktok"
    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30
    API_BASE = "https://open.tiktokapis.com/v2"
    PROFILE_URL_TEMPLATE = "https://www.tiktok.com/@{username}"

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        latency = lambda: int((time.monotonic() - start) * 1000)

        if payload.media_type != "video":
            return PublishResult(
                success=False,
                failure_class="invalid_media",
                retryable=False,
                error_message="TikTok publishing requires a video asset",
                latency_ms=latency(),
            )
        if not payload.media_urls:
            return PublishResult(
                success=False,
                failure_class="no_video_provided",
                retryable=False,
                error_message="TikTok requires a video URL",
                latency_ms=latency(),
            )

        try:
            import httpx

            caption = self._build_full_caption(payload)
            post_info = {
                "title": caption[:150],
                "privacy_level": self._extra.get(
                    "privacy_level", "PUBLIC_TO_EVERYONE"
                ),
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
            }
            source_info = {
                "source": "PULL_FROM_URL",
                "video_url": payload.media_urls[0],
            }

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.API_BASE}/post/publish/video/init/",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                    },
                    json={"post_info": post_info, "source_info": source_info},
                )

            body = _safe_json(resp) or {}
            data = body.get("data") or {}
            error = body.get("error") or {}

            if resp.status_code in (200, 201) and not error.get("code") in (
                "access_token_invalid",
                "scope_not_authorized",
            ):
                publish_id = data.get("publish_id") or data.get("publish_id_v2")
                if not publish_id:
                    return PublishResult(
                        success=False,
                        provider_response_code=resp.status_code,
                        failure_class="missing_publish_id",
                        retryable=True,
                        error_message="TikTok init returned no publish_id",
                        provider_response=body,
                        latency_ms=latency(),
                    )
                username = self._extra.get("platform_username")
                profile_url = (
                    self.PROFILE_URL_TEMPLATE.format(username=username)
                    if username
                    else None
                )
                return PublishResult(
                    success=True,
                    platform_post_id=publish_id,
                    platform_post_url=profile_url,
                    provider_response_code=resp.status_code,
                    provider_response=body,
                    latency_ms=latency(),
                )

            failure_class, retryable = _classify_tiktok_error(
                resp.status_code, error.get("code"),
            )
            return PublishResult(
                success=False,
                provider_response_code=resp.status_code,
                failure_class=failure_class,
                retryable=retryable,
                error_message=error.get("message") or resp.text[:500],
                provider_response=body,
                latency_ms=latency(),
            )

        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=latency(),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/user/info/",
                    params={"fields": "open_id"},
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.API_BASE}/oauth/token/",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "client_key": self._extra.get("client_key", ""),
                        "client_secret": self._extra.get("client_secret", ""),
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
                return resp.json()
        except Exception as exc:
            return {"error": str(exc)}


# ─── Shared helpers ───────────────────────────────────────────────────────────


def _safe_json(response: Any) -> dict | None:
    try:
        return response.json()
    except Exception:
        return None


def _classify_youtube_error(status_code: int) -> str:
    if status_code == 401:
        return "auth"
    if status_code == 403:
        return "forbidden"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "server_error"
    if status_code >= 400:
        return "client_error"
    return "unknown"


def _classify_tiktok_error(status_code: int, error_code: str | None) -> tuple[str, bool]:
    code = (error_code or "").lower()
    if status_code == 401 or "access_token" in code:
        return "auth", False
    if status_code == 429 or "rate_limit" in code:
        return "rate_limited", True
    if "spam" in code or "blocked" in code:
        return "policy_block", False
    if status_code >= 500:
        return "server_error", True
    return "client_error", False


# ─── Facebook ─────────────────────────────────────────────────────────────────


class FacebookAdapter(PlatformAdapter):
    """Facebook Graph API adapter for Page feed posts (text/photo/video)."""

    PLATFORM = "facebook"
    MAX_CAPTION_LENGTH = 63206
    MAX_HASHTAGS = 30
    API_BASE = "https://graph.facebook.com/v19.0"
    SUPPORTED_MEDIA = ["text", "image", "video"]

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        try:
            import httpx

            page_id = self._extra.get("page_id") or self._extra.get("platform_user_id")
            if not page_id:
                return PublishResult(
                    success=False,
                    failure_class="missing_page_id",
                    retryable=False,
                    error_message="Facebook page_id required",
                    latency_ms=int((time.monotonic() - start) * 1000),
                )

            caption = self._build_full_caption(payload)
            media_type = payload.media_type
            media_urls = payload.media_urls or []

            if media_type == "image" and media_urls:
                endpoint = f"{self.API_BASE}/{page_id}/photos"
                body = {
                    "url": media_urls[0],
                    "caption": caption,
                    "access_token": self._access_token,
                }
            elif media_type == "video" and media_urls:
                endpoint = f"{self.API_BASE}/{page_id}/videos"
                body = {
                    "file_url": media_urls[0],
                    "description": caption,
                    "access_token": self._access_token,
                }
            else:
                endpoint = f"{self.API_BASE}/{page_id}/feed"
                body = {
                    "message": caption,
                    "access_token": self._access_token,
                }
                if payload.link_url:
                    body["link"] = payload.link_url

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(endpoint, data=body)
                latency = int((time.monotonic() - start) * 1000)

                body_json = _safe_json(resp)
                if resp.status_code in (200, 201):
                    post_id = (
                        body_json.get("post_id")
                        or body_json.get("id")
                        or ""
                    )
                    return PublishResult(
                        success=True,
                        platform_post_id=str(post_id),
                        platform_post_url=f"https://www.facebook.com/{post_id}" if post_id else None,
                        provider_response_code=resp.status_code,
                        provider_response=body_json,
                        latency_ms=latency,
                    )

                err = (body_json.get("error") or {}) if isinstance(body_json, dict) else {}
                cls, retryable = _classify_facebook_error(resp.status_code, err)
                return PublishResult(
                    success=False,
                    provider_response_code=resp.status_code,
                    provider_response=body_json,
                    failure_class=cls,
                    retryable=retryable,
                    error_message=err.get("message") or resp.text,
                    latency_ms=latency,
                )
        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/me",
                    params={"access_token": self._access_token},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Facebook long-lived token exchange (no refresh_token in OAuth2 spec)."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.API_BASE}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self._extra.get("client_id", ""),
                        "client_secret": self._extra.get("client_secret", ""),
                        "fb_exchange_token": self._access_token,
                    },
                )
                return _safe_json(resp)
        except Exception as exc:
            return {"error": str(exc)}


def _classify_facebook_error(status_code: int, err: dict) -> tuple[str, bool]:
    code = err.get("code")
    sub = err.get("error_subcode")
    msg = (err.get("message") or "").lower()
    if status_code == 401 or code in (190, 102) or sub in (458, 460, 463, 467):
        return "auth", False
    if status_code == 429 or code in (4, 17, 32, 613):
        return "rate_limited", True
    if "permission" in msg or code in (200, 10):
        return "permissions", False
    if "spam" in msg or "policy" in msg:
        return "policy_block", False
    if status_code >= 500:
        return "server_error", True
    return "client_error", False


# ─── Pinterest ────────────────────────────────────────────────────────────────


class PinterestAdapter(PlatformAdapter):
    """Pinterest API v5 adapter for Pin creation."""

    PLATFORM = "pinterest"
    MAX_CAPTION_LENGTH = 500
    MAX_HASHTAGS = 20
    API_BASE = "https://api.pinterest.com/v5"
    SUPPORTED_MEDIA = ["image", "video"]

    async def publish(self, payload: PublishPayload) -> PublishResult:
        start = time.monotonic()
        try:
            import httpx

            board_id = self._extra.get("board_id")
            if not board_id:
                return PublishResult(
                    success=False,
                    failure_class="missing_board_id",
                    retryable=False,
                    error_message="Pinterest board_id required",
                    latency_ms=int((time.monotonic() - start) * 1000),
                )
            if not payload.media_urls:
                return PublishResult(
                    success=False,
                    failure_class="no_media_provided",
                    retryable=False,
                    error_message="Pinterest pin requires media_url",
                    latency_ms=int((time.monotonic() - start) * 1000),
                )

            title = (payload.caption or "").split("\n", 1)[0][:100]
            description = self._build_full_caption(payload)[: self.MAX_CAPTION_LENGTH]

            body: dict[str, Any] = {
                "board_id": board_id,
                "title": title,
                "description": description,
                "media_source": {
                    "source_type": "image_url",
                    "url": payload.media_urls[0],
                },
            }
            if payload.link_url:
                body["link"] = payload.link_url

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.API_BASE}/pins",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                latency = int((time.monotonic() - start) * 1000)
                body_json = _safe_json(resp)

                if resp.status_code in (200, 201):
                    pin_id = body_json.get("id") or ""
                    return PublishResult(
                        success=True,
                        platform_post_id=str(pin_id),
                        platform_post_url=f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else None,
                        provider_response_code=resp.status_code,
                        provider_response=body_json,
                        latency_ms=latency,
                    )

                cls, retryable = _classify_pinterest_error(resp.status_code, body_json)
                return PublishResult(
                    success=False,
                    provider_response_code=resp.status_code,
                    provider_response=body_json,
                    failure_class=cls,
                    retryable=retryable,
                    error_message=str(body_json.get("message") or resp.text),
                    latency_ms=latency,
                )
        except Exception as exc:
            return PublishResult(
                success=False,
                failure_class="exception",
                retryable=True,
                error_message=str(exc),
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def validate_token(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.API_BASE}/user_account",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.pinterest.com/v5/oauth/token",
                    auth=(
                        self._extra.get("client_id", ""),
                        self._extra.get("client_secret", ""),
                    ),
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
                return _safe_json(resp)
        except Exception as exc:
            return {"error": str(exc)}


def _classify_pinterest_error(status_code: int, body: dict) -> tuple[str, bool]:
    code = (body or {}).get("code")
    if status_code == 401 or code in (2, 7):
        return "auth", False
    if status_code == 429:
        return "rate_limited", True
    if status_code == 403:
        return "permissions", False
    if status_code >= 500:
        return "server_error", True
    return "client_error", False


# ─── Factory ──────────────────────────────────────────────────────────────────


ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "twitter": TwitterAdapter,
    "linkedin": LinkedInAdapter,
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "facebook": FacebookAdapter,
    "pinterest": PinterestAdapter,
}


def get_adapter(
    platform: str,
    access_token: str,
    **kwargs: Any,
) -> PlatformAdapter:
    """Get the appropriate platform adapter.

    Args:
        platform: Platform name (instagram, twitter, linkedin, youtube)
        access_token: Decrypted access token
        **kwargs: Platform-specific config (platform_user_id, author_urn, etc.)

    Returns:
        Configured platform adapter instance

    Raises:
        ValueError: If platform is not supported
    """
    adapter_cls = ADAPTERS.get(platform)
    if not adapter_cls:
        supported = ", ".join(sorted(ADAPTERS.keys()))
        raise ValueError(
            f"Unsupported platform: {platform}. Supported: {supported}"
        )
    return adapter_cls(access_token, **kwargs)
