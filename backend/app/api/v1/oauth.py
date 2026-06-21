"""OAuth API — handle social platform OAuth flows.

Provides OAuth initiation and callback handling for all supported platforms.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, and_

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.domains.control.models import SocialAccount, TokenStatus
from app.services.oauth.instagram import InstagramOAuth
from app.services.oauth.youtube import YouTubeOAuth
from app.services.oauth.tiktok import TikTokOAuth
from app.services.oauth.twitter import TwitterOAuth
from app.services.oauth.linkedin import LinkedInOAuth
from app.services.oauth.facebook import FacebookOAuth
from app.services.oauth.pinterest import PinterestOAuth
from app.services.oauth.base import OAuthError
from app.services.token_vault import get_vault
from app.core.logging import get_logger
from app.config import get_settings

router = APIRouter(prefix="/oauth", tags=["oauth"])
log = get_logger(__name__)

# OAuth service instances
oauth_services = {
    "instagram": InstagramOAuth(),
    "youtube": YouTubeOAuth(),
    "tiktok": TikTokOAuth(),
    "twitter": TwitterOAuth(),
    "linkedin": LinkedInOAuth(),
    "facebook": FacebookOAuth(),
    "pinterest": PinterestOAuth(),
}

OAUTH_STATE_TTL_SECONDS = 10 * 60

# Platforms that require PKCE on the OAuth 2.0 code flow.
_PKCE_PLATFORMS = {"twitter"}


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign_state_payload(payload: str) -> str:
    secret = get_settings().APP_SECRET_KEY.encode("utf-8")
    signature = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(signature)


def _create_oauth_state(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    code_verifier: str | None = None,
) -> str:
    """Create a signed, expiring OAuth state token.

    The callback cannot rely on cookies across all platform popup flows, so
    state is self-contained and HMAC-signed. ``code_verifier`` is included for
    PKCE flows; the callback must extract it to redeem the auth code.
    """
    body: Dict[str, Any] = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "nonce": uuid.uuid4().hex,
        "exp": int(time.time()) + OAUTH_STATE_TTL_SECONDS,
    }
    if code_verifier:
        body["cv"] = code_verifier
    payload = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_sign_state_payload(payload)}"


def _parse_oauth_state(state: str) -> Dict[str, Any]:
    """Validate OAuth state and return its decoded payload.

    Returns a dict with ``workspace_id`` (UUID) and optional ``code_verifier``.
    Legacy ``workspace_id:nonce`` states are accepted for backwards
    compatibility while in-flight authorizations finish.
    """
    try:
        payload, signature = state.split(".", 1)
        expected = _sign_state_payload(payload)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")

        data = json.loads(_b64url_decode(payload))
        if int(data.get("exp", 0)) < int(time.time()):
            raise ValueError("state expired")
        return {
            "workspace_id": uuid.UUID(str(data["workspace_id"])),
            "code_verifier": data.get("cv"),
        }
    except Exception as exc:
        # SECURITY: no unsigned/legacy fallback. An unsigned "workspace_id:nonce"
        # state is attacker-forgeable and would let a malicious callback bind a
        # social account (and its tokens) into an arbitrary victim workspace —
        # cross-tenant account injection. Reject anything not HMAC-signed.
        raise ValueError("invalid OAuth state") from exc


def _generate_pkce_verifier() -> str:
    """Cryptographically random PKCE code_verifier (RFC 7636, 43-128 chars)."""
    return secrets.token_urlsafe(64)


@router.get("/platforms")
async def list_platforms() -> JSONResponse:
    """List all supported OAuth platforms."""
    platforms = []
    for platform_key, service in oauth_services.items():
        platforms.append({
            "key": platform_key,
            "name": service.platform_name,
            "scopes": service.required_scopes,
            "supports_publishing": service.supports_publishing,
            "supports_analytics": service.supports_analytics,
        })
    
    return JSONResponse({"platforms": platforms})


@router.get("/{platform}/authorize")
async def initiate_oauth(
    platform: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    request: Request,
) -> RedirectResponse:
    """Initiate OAuth flow for a platform."""
    if platform not in oauth_services:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    service = oauth_services[platform]

    # Config-present guard: never redirect to a half-built authorize URL when the
    # platform's app credentials are not set on this server.
    if not service.client_id or not service.client_secret:
        raise HTTPException(
            status_code=503,
            detail=f"{service.platform_name} is not configured on this server yet.",
        )

    code_verifier = _generate_pkce_verifier() if platform in _PKCE_PLATFORMS else None

    # Generate signed state parameter for CSRF protection
    state = _create_oauth_state(
        workspace.id, current_user.id, code_verifier=code_verifier,
    )

    # Build redirect URI
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/v1/oauth/{platform}/callback"

    try:
        # Get authorization URL
        auth_url = service.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )
        
        log.info("oauth.initiate", 
                platform=platform, 
                workspace_id=str(workspace.id),
                user_id=str(current_user.id))
        
        return RedirectResponse(url=auth_url)
        
    except OAuthError as e:
        log.error("oauth.initiate.failed", 
                 platform=platform, 
                 error=str(e),
                 workspace_id=str(workspace.id))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    request: Request,
    db: DbSession,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
) -> RedirectResponse:
    """Handle OAuth callback from platform."""
    if platform not in oauth_services:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Handle OAuth error
    if error:
        log.error("oauth.callback.error", 
                 platform=platform, 
                 error=error)
        return RedirectResponse(url=f"/settings/accounts?error={error}")
    
    try:
        state_data = _parse_oauth_state(state)
        workspace_id = state_data["workspace_id"]
        code_verifier = state_data.get("code_verifier")
    except ValueError:
        log.error("oauth.callback.invalid_state",
                 platform=platform,
                 state=state)
        return RedirectResponse(url="/settings/accounts?error=invalid_state")
    
    service = oauth_services[platform]
    
    # Build redirect URI
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/v1/oauth/{platform}/callback"
    
    try:
        # Exchange code for tokens
        token_data = await service.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
        
        # Get user profile
        profile = await service.get_user_profile(token_data["access_token"])
        
        # Check if account already exists
        result = await db.execute(
            select(SocialAccount).where(
                and_(
                    SocialAccount.workspace_id == workspace_id,
                    SocialAccount.platform == platform,
                    SocialAccount.platform_user_id == profile["id"],
                )
            )
        )
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            # Update existing account
            existing_account.platform_username = profile.get("username")
            existing_account.platform_display_name = profile.get("display_name")
            existing_account.platform_avatar_url = profile.get("avatar_url")
            existing_account.platform_url = profile.get("profile_url")
            existing_account.followers_count = profile.get("followers_count", 0)
            existing_account.following_count = profile.get("following_count", 0)
            existing_account.posts_count = profile.get("posts_count", 0)
            existing_account.is_active = True
            existing_account.token_status = TokenStatus.VALID
            existing_account.last_synced_at = datetime.now(timezone.utc)
            existing_account.updated_at = datetime.now(timezone.utc)
            
            # Update encrypted tokens
            vault = get_vault()
            existing_account.encrypted_access_token = vault.encrypt(
                token_data["access_token"],
                workspace_id,
            )
            if token_data.get("refresh_token"):
                existing_account.encrypted_refresh_token = vault.encrypt(
                    token_data["refresh_token"],
                    workspace_id,
                )
            existing_account.token_expires_at = token_data.get("expires_at")
            
            account = existing_account
        else:
            # Create new account
            vault = get_vault()
            
            # Check if this is the first account for this platform
            count_result = await db.execute(
                select(SocialAccount).where(
                    and_(
                        SocialAccount.workspace_id == workspace_id,
                        SocialAccount.platform == platform,
                        SocialAccount.is_active == True,
                    )
                )
            )
            is_first = len(count_result.scalars().all()) == 0
            
            account = SocialAccount(
                workspace_id=workspace_id,
                platform=platform,
                platform_user_id=profile["id"],
                platform_username=profile.get("username"),
                platform_display_name=profile.get("display_name"),
                platform_avatar_url=profile.get("avatar_url"),
                platform_url=profile.get("profile_url"),
                encrypted_access_token=vault.encrypt(
                    token_data["access_token"],
                    workspace_id,
                ),
                encrypted_refresh_token=(
                    vault.encrypt(token_data["refresh_token"], workspace_id)
                    if token_data.get("refresh_token")
                    else None
                ),
                token_expires_at=token_data.get("expires_at"),
                token_scope=token_data.get("scope"),
                followers_count=profile.get("followers_count", 0),
                following_count=profile.get("following_count", 0),
                posts_count=profile.get("posts_count", 0),
                is_active=True,
                is_primary=is_first,
                token_status=TokenStatus.VALID,
                last_synced_at=datetime.now(timezone.utc),
            )
            db.add(account)
        
        await db.commit()
        
        log.info("oauth.callback.success", 
                platform=platform, 
                workspace_id=str(workspace_id),
                account_id=str(account.id),
                username=profile.get("username"))
        
        return RedirectResponse(url="/settings/accounts?success=connected")
        
    except OAuthError as e:
        log.error("oauth.callback.failed", 
                 platform=platform, 
                 error=str(e),
                 workspace_id=str(workspace_id))
        return RedirectResponse(url=f"/settings/accounts?error={str(e)}")
    except Exception as e:
        log.error("oauth.callback.unexpected", 
                 platform=platform, 
                 error=str(e),
                 workspace_id=str(workspace_id))
        return RedirectResponse(url="/settings/accounts?error=unexpected_error")


# ─── Credential-based connect (Mastodon, Bluesky) ─────────────────────────────
# These platforms have no central redirect-OAuth app: Mastodon is per-instance
# (paste a token created in the instance), Bluesky uses a handle + app-password.
# Tokens are stored with the same per-workspace envelope encryption as OAuth.

from pydantic import BaseModel, Field  # noqa: E402


class MastodonConnectRequest(BaseModel):
    instance_url: str = Field(..., max_length=300)
    access_token: str = Field(..., min_length=10, max_length=500)


class BlueskyConnectRequest(BaseModel):
    handle: str = Field(..., max_length=300)
    app_password: str = Field(..., min_length=8, max_length=200)
    pds_url: str | None = Field(default=None, max_length=300)


async def _upsert_credential_account(
    db,
    *,
    workspace_id: uuid.UUID,
    platform: str,
    platform_user_id: str,
    platform_username: str | None,
    display_name: str | None,
    base_url: str,
    access_token: str,
    scope: str,
) -> SocialAccount:
    """Create or update a SocialAccount connected via pasted credentials.

    ``base_url`` is stored in ``platform_url`` because the publish adapters read
    the instance / PDS endpoint from there.
    """
    vault = get_vault()
    enc = vault.encrypt(access_token, workspace_id)

    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.workspace_id == workspace_id,
                SocialAccount.platform == platform,
                SocialAccount.platform_user_id == platform_user_id,
            )
        )
    )
    account = result.scalar_one_or_none()

    if account:
        account.platform_username = platform_username
        account.platform_display_name = display_name
        account.platform_url = base_url
        account.encrypted_access_token = enc
        account.token_scope = scope
        account.token_status = TokenStatus.VALID
        account.is_active = True
        account.last_synced_at = datetime.now(timezone.utc)
        account.updated_at = datetime.now(timezone.utc)
    else:
        count_result = await db.execute(
            select(SocialAccount).where(
                and_(
                    SocialAccount.workspace_id == workspace_id,
                    SocialAccount.platform == platform,
                    SocialAccount.is_active == True,
                )
            )
        )
        is_first = len(count_result.scalars().all()) == 0
        account = SocialAccount(
            workspace_id=workspace_id,
            platform=platform,
            platform_user_id=platform_user_id,
            platform_username=platform_username,
            platform_display_name=display_name,
            platform_url=base_url,
            encrypted_access_token=enc,
            token_scope=scope,
            is_active=True,
            is_primary=is_first,
            token_status=TokenStatus.VALID,
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(account)

    await db.commit()
    await db.refresh(account)
    return account


@router.post("/mastodon/connect")
async def connect_mastodon(
    body: MastodonConnectRequest,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Connect a Mastodon account via an instance access token."""
    import httpx

    instance = body.instance_url.strip().rstrip("/")
    if not instance.startswith("http"):
        instance = f"https://{instance}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{instance}/api/v1/accounts/verify_credentials",
                headers={"Authorization": f"Bearer {body.access_token}"},
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Invalid Mastodon instance or access token.",
            )
        prof = resp.json()
    except HTTPException:
        raise
    except Exception:
        log.warning("oauth.mastodon.connect_unreachable", instance=instance)
        raise HTTPException(
            status_code=400,
            detail="Could not reach the Mastodon instance. Check the URL and try again.",
        )

    mastodon_id = prof.get("id")
    if not mastodon_id:
        raise HTTPException(
            status_code=400, detail="Mastodon did not return an account id."
        )

    account = await _upsert_credential_account(
        db,
        workspace_id=workspace.id,
        platform="mastodon",
        platform_user_id=str(mastodon_id),
        platform_username=prof.get("username"),
        display_name=prof.get("display_name") or prof.get("username"),
        base_url=instance,
        access_token=body.access_token,
        scope="write:statuses",
    )
    log.info(
        "oauth.mastodon.connected",
        workspace_id=str(workspace.id), account_id=str(account.id),
    )
    return JSONResponse(
        {
            "id": str(account.id),
            "platform": "mastodon",
            "username": prof.get("username"),
            "instance": instance,
        }
    )


@router.post("/bluesky/connect")
async def connect_bluesky(
    body: BlueskyConnectRequest,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Connect a Bluesky account via handle + app-password."""
    import httpx

    pds = (body.pds_url or "https://bsky.social").strip().rstrip("/")
    if not pds.startswith("http"):
        pds = f"https://{pds}"
    handle = body.handle.strip().lstrip("@")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{pds}/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": body.app_password},
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Invalid Bluesky handle or app password.",
            )
        session = resp.json()
    except HTTPException:
        raise
    except Exception:
        log.warning("oauth.bluesky.connect_unreachable", pds=pds)
        raise HTTPException(
            status_code=400,
            detail="Could not reach the Bluesky service. Check your handle and try again.",
        )

    did = session.get("did")
    if not did:
        raise HTTPException(
            status_code=400, detail="Bluesky did not return an account id."
        )
    resolved_handle = session.get("handle") or handle
    account = await _upsert_credential_account(
        db,
        workspace_id=workspace.id,
        platform="bluesky",
        platform_user_id=str(did),
        platform_username=resolved_handle,
        display_name=resolved_handle,
        base_url=pds,
        access_token=body.app_password,
        scope="post",
    )
    log.info(
        "oauth.bluesky.connected",
        workspace_id=str(workspace.id), account_id=str(account.id),
    )
    return JSONResponse(
        {
            "id": str(account.id),
            "platform": "bluesky",
            "handle": resolved_handle,
            "did": did,
        }
    )


@router.post("/{platform}/refresh")
async def refresh_token(
    platform: str,
    account_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Refresh OAuth token for an account."""
    if platform not in oauth_services:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Get account
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.platform == platform,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.encrypted_refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")
    
    service = oauth_services[platform]
    vault = get_vault()
    
    try:
        # Decrypt refresh token
        refresh_token = vault.decrypt(account.encrypted_refresh_token, workspace.id)
        
        # Refresh tokens
        token_data = await service.refresh_access_token(refresh_token)
        
        # Update account
        account.encrypted_access_token = vault.encrypt(
            token_data["access_token"],
            workspace.id,
        )
        if token_data.get("refresh_token"):
            account.encrypted_refresh_token = vault.encrypt(
                token_data["refresh_token"],
                workspace.id,
            )
        account.token_expires_at = token_data.get("expires_at")
        account.token_status = TokenStatus.VALID
        account.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        log.info("oauth.refresh.success", 
                platform=platform, 
                account_id=account_id)
        
        return JSONResponse({"refreshed": True, "account_id": account_id})
        
    except OAuthError as e:
        log.error("oauth.refresh.failed", 
                 platform=platform, 
                 account_id=account_id,
                 error=str(e))
        
        # Mark token as expired/revoked
        account.token_status = TokenStatus.REVOKED
        await db.commit()
        
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{platform}/revoke")
async def revoke_token(
    platform: str,
    account_id: str,
    current_user: CurrentUser,
    workspace: CurrentWorkspace,
    db: DbSession,
) -> JSONResponse:
    """Revoke OAuth token for an account."""
    if platform not in oauth_services:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Get account
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == uuid.UUID(account_id),
                SocialAccount.workspace_id == workspace.id,
                SocialAccount.platform == platform,
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    service = oauth_services[platform]
    vault = get_vault()
    
    try:
        # Decrypt access token and revoke token on platform if available.
        if account.encrypted_access_token:
            access_token = vault.decrypt(account.encrypted_access_token, workspace.id)
            await service.revoke_token(access_token)
        
        log.info("oauth.revoke.success", 
                platform=platform, 
                account_id=account_id)
        
    except OAuthError as e:
        log.warning("oauth.revoke.failed", 
                   platform=platform, 
                   account_id=account_id,
                   error=str(e))
        # Continue anyway - we'll mark as revoked locally
    
    # Mark account as revoked locally
    account.token_status = TokenStatus.REVOKED
    account.is_active = False
    account.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return JSONResponse({"revoked": True, "account_id": account_id})
