"""Media service — validates, uploads, and manages media files via S3-compatible storage."""

from __future__ import annotations

import io
import uuid
from pathlib import PurePosixPath
from typing import Optional

import aiobotocore.session
import structlog
from fastapi import UploadFile

from app.config import get_settings
from app.constants import (
    ALLOWED_MIME_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOAD_CHUNK_SIZE,
)
from app.exceptions import MediaError, StorageError

logger = structlog.get_logger(__name__)
settings = get_settings()


class MediaService:
    """Handles media upload/delete with S3-compatible storage (MinIO in dev, S3 in prod)."""

    # ── Validation ────────────────────────────────────────────────────────

    def validate(self, file: UploadFile) -> None:
        """Raise MediaError if the file is not acceptable."""
        if not file.filename:
            raise MediaError("Filename is required")

        ext = PurePosixPath(file.filename).suffix.lower()
        if not ext:
            raise MediaError("File must have an extension")

        content_type = (file.content_type or "").lower()
        if content_type not in ALLOWED_MIME_TYPES:
            raise MediaError(
                f"File type '{content_type}' is not allowed. "
                "Accepted types: JPEG, PNG, WebP, GIF, MP4, MOV, AVI, WebM"
            )

        if file.size is not None and file.size > MAX_UPLOAD_SIZE_BYTES:
            size_mb = file.size / (1024 * 1024)
            limit_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise MediaError(f"File too large ({size_mb:.1f} MB). Maximum: {limit_mb:.0f} MB")

    def detect_media_type(self, content_type: str) -> str:
        """Return 'image', 'video', or 'text'."""
        ct = content_type.lower()
        if ct.startswith("image/"):
            return "image"
        if ct.startswith("video/"):
            return "video"
        return "text"

    # ── Upload ────────────────────────────────────────────────────────────

    async def upload(self, file: UploadFile, user_id: str) -> tuple[str, str]:
        """
        Upload file to S3. Returns (s3_key, public_url).
        Reads in chunks to handle large files without loading all into memory.
        """
        self.validate(file)

        ext = PurePosixPath(file.filename or "upload").suffix.lower()
        media_type = self.detect_media_type(file.content_type or "")
        s3_key = f"media/{user_id}/{uuid.uuid4().hex}{ext}"

        # Stream file into memory buffer in chunks, enforcing size limit
        buffer = io.BytesIO()
        total_size = 0
        try:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise MediaError("File exceeded maximum size during upload")
                buffer.write(chunk)
        finally:
            await file.close()

        buffer.seek(0)

        try:
            session = aiobotocore.session.get_session()
            async with session.create_client(
                "s3",
                region_name=settings.S3_REGION,
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            ) as client:
                await client.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=buffer.read(),
                    ContentType=file.content_type or "application/octet-stream",
                )
        except Exception as exc:
            logger.error("s3_upload_failed", key=s3_key, error=str(exc))
            raise StorageError(f"Failed to upload media: {exc}") from exc

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{s3_key}"
        logger.info("media_uploaded", key=s3_key, size_bytes=total_size)
        return s3_key, public_url

    # ── Delete ────────────────────────────────────────────────────────────

    async def delete(self, s3_key: str) -> None:
        """Delete a media file from S3. Non-fatal on failure."""
        if not s3_key:
            return
        try:
            session = aiobotocore.session.get_session()
            async with session.create_client(
                "s3",
                region_name=settings.S3_REGION,
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            ) as client:
                await client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
            logger.info("media_deleted", key=s3_key)
        except Exception as exc:
            logger.warning("media_delete_failed", key=s3_key, error=str(exc))
