"""Social Accounts API — connect, disconnect, list, health check.

Workspace-scoped. Manages OAuth-connected platform accounts.
"""
from __future__ import annotations

from typing import Annotated
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, update

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession, require_workspace_role
from app.domains.control.models import SocialAccount, TokenStatus
from app.exceptions import NotFoundError

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


def _account_to_dict(account: SocialAccount) -> dict:
    """Serialize a social account (never expose tokens)."""
    return {
        "id": str(account.id),
        "platform": account.platform,
        "platform_username": account.platform_username,
        "platform_display_name": account.platform_display_name,
        "platform_avatar_url": account.platform_avatar_url,
        "platform_url": account.platform_url,
        "token_status": account.token_status.value,
        "followers_count": account.followers_count,
        "following_count": account.following_count,
        "posts_count": account.posts_count,
        "engagement_rate": account.engagement_rate,
        "is_active": account.is_active,
        "is_primary": account.is_primary,
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
        "last_validated_at": (
            account.last_validated_at.isoformat() if account.last_validated_at else None
        ),
        "created_at": account.created_at.isoformat(),
    }


@router.get("")
async def list_accounts(
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
    platform: str | None = Query(None),
    include_inactive: bool = Query(False),
) -> JSONResponse:
    """List all connected social accounts for the workspace."""
    filters = [SocialAccount.workspace_id == workspace.id]
    if platform:
        filters.append(SocialAccount.platform == platform)
    if not include_inactive:
        filters.append(SocialAccount.is_active == True)

    result = await db.execute(
        select(SocialAccount)
        .where(and_(*filters))
        .order_by(SocialAccount.is_primary.desc(), SocialAccount.created_at.desc())
    )
    accounts = result.scalars().all()

    return JSONResponse({
        "accounts": [_account_to_dict(a) for a in accounts],
        "total": len(accounts),
    })


@router.get("/{account_id}")
async def get_account(
    account_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Get a specific social account."""
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("SocialAccount", account_id)

    return JSONResponse({"account": _account_to_dict(account)})


@router.post("")
async def connect_account(
    body: dict,
    current_user: CurrentUser,
    workspace: Annotated[object, Depends(require_workspace_role("editor"))],
    db: DbSession,
) -> JSONResponse:
    """Manually register a social account (for dev/testing).

    In production, this would be handled by the OAuth callback flow.
    """
    required_fields = ["platform", "platform_user_id"]
    for field in required_fields:
        if not body.get(field):
            return JSONResponse({"error": f"{field} is required"}, status_code=400)

    # Check existing
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.platform == body["platform"],
                SocialAccount.platform_user_id == body["platform_user_id"],
            )
        )
    )
    if result.scalar_one_or_none():
        return JSONResponse(
            {"error": "Account already connected"}, status_code=409,
        )

    # Check if this is the first account for this platform
    count_result = await db.execute(
        select(func.count(SocialAccount.id)).where(
            and_(
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.platform == body["platform"],
            )
        )
    )
    is_first = (count_result.scalar() or 0) == 0

    encrypted_access_token = None
    encrypted_refresh_token = None
    token_status = TokenStatus.EXPIRED
    if body.get("access_token"):
        from app.services.token_vault import get_vault

        vault = get_vault()
        encrypted_access_token = vault.encrypt(body["access_token"], workspace.id)
        encrypted_refresh_token = (
            vault.encrypt(body["refresh_token"], workspace.id)
            if body.get("refresh_token")
            else None
        )
        token_status = TokenStatus.VALID

    account = SocialAccount(
        workspace_id=workspace.id,
        platform=body["platform"],
        platform_user_id=body["platform_user_id"],
        platform_username=body.get("platform_username"),
        platform_display_name=body.get("platform_display_name"),
        platform_avatar_url=body.get("platform_avatar_url"),
        platform_url=body.get("platform_url"),
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        token_status=token_status,
        is_primary=is_first,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    await db.commit()

    return JSONResponse(
        {"account": _account_to_dict(account)},
        status_code=201,
    )


@router.delete("/{account_id}")
async def disconnect_account(
    account_id: str,
    current_user: CurrentUser,
    workspace: Annotated[object, Depends(require_workspace_role("editor"))],
    db: DbSession,
) -> JSONResponse:
    """Disconnect (deactivate) a social account. Requires EDITOR+."""
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("SocialAccount", account_id)

    account.is_active = False
    account.token_status = TokenStatus.REVOKED
    account.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return JSONResponse({"disconnected": True, "account_id": account_id})


@router.post("/{account_id}/set-primary")
async def set_primary(
    account_id: str,
    current_user: CurrentUser,
    workspace: Annotated[object, Depends(require_workspace_role("editor"))],
    db: DbSession,
) -> JSONResponse:
    """Set an account as the primary for its platform. Requires EDITOR+."""
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("SocialAccount", account_id)

    # Unset other primaries for this platform
    await db.execute(
        update(SocialAccount)
        .where(
            and_(
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.platform == account.platform,
                SocialAccount.id != account.id,
            )
        )
        .values(is_primary=False)
    )
    account.is_primary = True
    await db.commit()

    return JSONResponse({"primary": True, "account_id": account_id})


@router.get("/{account_id}/health")
async def check_health(
    account_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Check the health of a social account's connection."""
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("SocialAccount", account_id)

    # Determine health status
    is_healthy = account.token_status == TokenStatus.VALID and account.is_active
    needs_refresh = account.token_status == TokenStatus.EXPIRED
    needs_reauth = account.token_status == TokenStatus.REVOKED

    return JSONResponse({
        "account_id": account_id,
        "platform": account.platform,
        "is_healthy": is_healthy,
        "token_status": account.token_status.value,
        "needs_refresh": needs_refresh,
        "needs_reauth": needs_reauth,
        "last_validated_at": (
            account.last_validated_at.isoformat() if account.last_validated_at else None
        ),
        "rate_limit_state": account.rate_limit_state or {},
    })
