"""Media API — /media library + upload, matching frontend api-client paths.

Wraps the existing ContentAsset model and MediaService.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, MediaSvc
from app.config import get_settings
from app.domains.execution.models import ContentAsset

router = APIRouter(prefix="/media", tags=["media"])


class MediaItemOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    mime_type: str
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: str


class MediaListResponse(BaseModel):
    items: list[MediaItemOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_url: str
    file_id: uuid.UUID
    expires_at: str


class DeleteMultipleRequest(BaseModel):
    ids: list[uuid.UUID]


class ThumbnailRequest(BaseModel):
    time: float | None = None


def _public_url(storage_key: str) -> str:
    settings = get_settings()
    base = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
    return f"{base}/{storage_key}" if base else storage_key


def _to_item(asset: ContentAsset, user_id: uuid.UUID) -> MediaItemOut:
    meta = asset.metadata_ or {}
    return MediaItemOut(
        id=asset.id,
        user_id=user_id,
        filename=PurePosixPath(asset.storage_key).name,
        original_filename=asset.original_filename or PurePosixPath(asset.storage_key).name,
        file_type=asset.media_kind,
        file_size=asset.file_size_bytes or 0,
        mime_type=asset.mime_type or "application/octet-stream",
        url=_public_url(asset.storage_key),
        thumbnail_url=meta.get("thumbnail_url"),
        width=asset.width,
        height=asset.height,
        duration=asset.duration_seconds,
        metadata=meta,
        created_at=asset.created_at.isoformat(),
    )


@router.get("", response_model=MediaListResponse)
async def list_media(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    file_type: str | None = None,
    sort_by: Annotated[str, Query(pattern="^(created_at|original_filename|file_size_bytes|filename|file_size)$")] = "created_at",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> MediaListResponse:
    q = select(ContentAsset).where(ContentAsset.workspace_id == workspace.id)
    if file_type:
        q = q.where(ContentAsset.media_kind == file_type)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()

    sort_field_map = {
        "created_at": ContentAsset.created_at,
        "original_filename": ContentAsset.original_filename,
        "filename": ContentAsset.original_filename,
        "file_size_bytes": ContentAsset.file_size_bytes,
        "file_size": ContentAsset.file_size_bytes,
    }
    field = sort_field_map[sort_by]
    q = q.order_by(field.desc() if sort_order == "desc" else field.asc())
    q = q.limit(page_size).offset((page - 1) * page_size)
    rows = list((await db.execute(q)).scalars().all())

    return MediaListResponse(
        items=[_to_item(a, user.id) for a in rows],
        total=int(total),
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < int(total),
    )


async def _load_asset(db, workspace_id: uuid.UUID, asset_id: uuid.UUID) -> ContentAsset:
    a = (
        await db.execute(
            select(ContentAsset).where(
                ContentAsset.id == asset_id,
                ContentAsset.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Media not found")
    return a


@router.get("/{asset_id}", response_model=MediaItemOut)
async def get_media(
    asset_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> MediaItemOut:
    return _to_item(await _load_asset(db, workspace.id, asset_id), user.id)


@router.post("/upload", response_model=MediaItemOut, status_code=201)
async def upload_media(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    media: MediaSvc,
    file: Annotated[UploadFile, File(...)],
) -> MediaItemOut:
    storage_key, _ = await media.upload(file, user_id=str(user.id))
    media_kind = media.detect_media_type(file.content_type or "")

    asset = ContentAsset(
        workspace_id=workspace.id,
        storage_key=storage_key,
        media_kind=media_kind,
        original_filename=file.filename,
        file_size_bytes=file.size,
        mime_type=file.content_type,
        source_lineage="upload",
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return _to_item(asset, user.id)


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def presigned_url(
    body: PresignedUrlRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
) -> PresignedUrlResponse:
    """Generate a presigned PUT URL for direct upload.

    Falls back to the local /media/upload endpoint when S3 is not configured.
    """
    settings = get_settings()
    file_id = uuid.uuid4()
    ext = PurePosixPath(body.filename).suffix.lower()
    storage_key = f"media/{user.id}/{file_id.hex}{ext}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    if not settings.S3_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
        return PresignedUrlResponse(
            upload_url="/api/v1/media/upload",
            file_url=_public_url(storage_key),
            file_id=file_id,
            expires_at=expires_at.isoformat(),
        )

    try:
        import aiobotocore.session

        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        ) as client:
            url = await client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": storage_key,
                    "ContentType": body.content_type,
                },
                ExpiresIn=900,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to sign URL: {exc}")

    return PresignedUrlResponse(
        upload_url=url,
        file_url=_public_url(storage_key),
        file_id=file_id,
        expires_at=expires_at.isoformat(),
    )


@router.delete("/{asset_id}", status_code=204, response_model=None)
async def delete_media(
    asset_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    media: MediaSvc,
) -> None:
    a = await _load_asset(db, workspace.id, asset_id)
    try:
        await media.delete(a.storage_key)
    except Exception:
        pass
    await db.delete(a)
    await db.flush()


@router.post("/delete-multiple", status_code=204, response_model=None)
async def delete_multiple_media(
    body: DeleteMultipleRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    media: MediaSvc,
) -> None:
    rows = list(
        (
            await db.execute(
                select(ContentAsset).where(
                    ContentAsset.workspace_id == workspace.id,
                    ContentAsset.id.in_(body.ids),
                )
            )
        )
        .scalars()
        .all()
    )
    for a in rows:
        try:
            await media.delete(a.storage_key)
        except Exception:
            pass
        await db.delete(a)
    await db.flush()


@router.post("/{asset_id}/process", response_model=MediaItemOut)
async def process_video(
    asset_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> MediaItemOut:
    """Mark a video as processed. Heavy processing is delegated to workers."""
    a = await _load_asset(db, workspace.id, asset_id)
    meta = dict(a.metadata_ or {})
    meta["processed"] = True
    meta["processed_at"] = datetime.now(timezone.utc).isoformat()
    a.metadata_ = meta
    await db.flush()
    await db.refresh(a)
    return _to_item(a, user.id)


@router.post("/{asset_id}/thumbnail")
async def generate_thumbnail(
    asset_id: uuid.UUID,
    body: ThumbnailRequest,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> dict[str, Any]:
    """Stub thumbnail generation. Returns the placeholder URL stored on the asset (if any)."""
    a = await _load_asset(db, workspace.id, asset_id)
    meta = dict(a.metadata_ or {})
    thumbnail_url = meta.get("thumbnail_url") or _public_url(a.storage_key)
    meta["thumbnail_url"] = thumbnail_url
    a.metadata_ = meta
    await db.flush()
    return {"thumbnail_url": thumbnail_url}
