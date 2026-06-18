"""Storage Service — S3-compatible async file operations.

Supports AWS S3, Cloudflare R2, MinIO, and any S3-compatible storage.
Uses aiobotocore for async operations to prevent blocking FastAPI.

Key operations:
  - Generate presigned upload URLs (direct client → S3)
  - Download files to worker /tmp for processing
  - Upload processed files back to S3
  - Generate presigned download URLs for frontend preview
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

import structlog
from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from app.config import get_settings

logger = structlog.get_logger(__name__)

# Presigned URL expiry times
UPLOAD_URL_EXPIRY = timedelta(hours=1)
DOWNLOAD_URL_EXPIRY = timedelta(hours=24)


class StorageService:
    """S3-compatible async storage operations."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session = get_session()

    def _get_client_config(self) -> dict:
        """Build aiobotocore client configuration."""
        config = {
            "aws_access_key_id": self._settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": self._settings.S3_SECRET_ACCESS_KEY,
            "region_name": self._settings.S3_REGION,
        }
        if self._settings.S3_ENDPOINT_URL:
            config["endpoint_url"] = self._settings.S3_ENDPOINT_URL
        return config

    async def generate_presigned_upload_url(
        self,
        workspace_id: uuid.UUID,
        filename: str,
        content_type: str = "video/mp4",
    ) -> tuple[str, str]:
        """Generate presigned URL for direct client upload to S3.

        Args:
            workspace_id: Workspace UUID for path scoping
            filename: Original filename
            content_type: MIME type

        Returns:
            Tuple of (presigned_url, s3_key)
        """
        # Generate unique S3 key
        file_ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"workspaces/{workspace_id}/raw/{unique_name}"

        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                url = await client.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self._settings.S3_BUCKET_NAME,
                        "Key": s3_key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=int(UPLOAD_URL_EXPIRY.total_seconds()),
                )
                logger.info(
                    "presigned_upload_url_generated",
                    workspace_id=str(workspace_id),
                    s3_key=s3_key,
                )
                return url, s3_key
            except ClientError as exc:
                logger.error(
                    "presigned_upload_url_failed",
                    workspace_id=str(workspace_id),
                    error=str(exc),
                )
                raise

    async def generate_presigned_download_url(
        self,
        s3_key: str,
        expiry: timedelta = DOWNLOAD_URL_EXPIRY,
    ) -> str:
        """Generate presigned URL for downloading a file.

        Args:
            s3_key: S3 object key
            expiry: URL expiration time

        Returns:
            Presigned download URL
        """
        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self._settings.S3_BUCKET_NAME,
                        "Key": s3_key,
                    },
                    ExpiresIn=int(expiry.total_seconds()),
                )
                return url
            except ClientError as exc:
                logger.error(
                    "presigned_download_url_failed",
                    s3_key=s3_key,
                    error=str(exc),
                )
                raise

    async def download_file_to_tmp(
        self,
        s3_key: str,
        local_path: Path,
    ) -> None:
        """Download S3 file to local /tmp for processing.

        Args:
            s3_key: S3 object key
            local_path: Local filesystem path
        """
        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                response = await client.get_object(
                    Bucket=self._settings.S3_BUCKET_NAME,
                    Key=s3_key,
                )
                async with response["Body"] as stream:
                    data = await stream.read()
                    local_path.write_bytes(data)

                logger.info(
                    "file_downloaded",
                    s3_key=s3_key,
                    local_path=str(local_path),
                    size_bytes=len(data),
                )
            except ClientError as exc:
                logger.error(
                    "file_download_failed",
                    s3_key=s3_key,
                    error=str(exc),
                )
                raise

    async def upload_file_from_tmp(
        self,
        local_path: Path,
        destination_key: str,
        content_type: str = "video/mp4",
    ) -> str:
        """Upload processed file from /tmp back to S3.

        Args:
            local_path: Local filesystem path
            destination_key: Target S3 key
            content_type: MIME type

        Returns:
            S3 key of uploaded file
        """
        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                data = local_path.read_bytes()
                await client.put_object(
                    Bucket=self._settings.S3_BUCKET_NAME,
                    Key=destination_key,
                    Body=data,
                    ContentType=content_type,
                )
                logger.info(
                    "file_uploaded",
                    local_path=str(local_path),
                    s3_key=destination_key,
                    size_bytes=len(data),
                )
                return destination_key
            except ClientError as exc:
                logger.error(
                    "file_upload_failed",
                    local_path=str(local_path),
                    error=str(exc),
                )
                raise

    async def delete_file(self, s3_key: str) -> None:
        """Delete a file from S3.

        Args:
            s3_key: S3 object key
        """
        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                await client.delete_object(
                    Bucket=self._settings.S3_BUCKET_NAME,
                    Key=s3_key,
                )
                logger.info("file_deleted", s3_key=s3_key)
            except ClientError as exc:
                logger.error(
                    "file_delete_failed",
                    s3_key=s3_key,
                    error=str(exc),
                )
                raise

    async def get_file_metadata(self, s3_key: str) -> dict:
        """Get file metadata without downloading.

        Args:
            s3_key: S3 object key

        Returns:
            Metadata dict with size, content_type, etc.
        """
        async with self._session.create_client("s3", **self._get_client_config()) as client:
            try:
                response = await client.head_object(
                    Bucket=self._settings.S3_BUCKET_NAME,
                    Key=s3_key,
                )
                return {
                    "size_bytes": response.get("ContentLength", 0),
                    "content_type": response.get("ContentType", ""),
                    "last_modified": response.get("LastModified"),
                    "etag": response.get("ETag", "").strip('"'),
                }
            except ClientError as exc:
                logger.error(
                    "file_metadata_failed",
                    s3_key=s3_key,
                    error=str(exc),
                )
                raise


# Singleton accessor
_storage_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create the global StorageService singleton."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
