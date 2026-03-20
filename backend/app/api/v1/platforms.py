"""Platform OAuth connection routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.api.deps import CurrentUser, AuthSvc, DbSession
from app.config import get_settings

router = APIRouter(prefix="/platforms", tags=["platforms"])

# ── Credential registry ────────────────────────────────────────────────────
# Maps platform id → (settings attribute, human-readable name)
_PLATFORM_CREDS: dict[str, tuple[str, str]] = {
    "instagram":      ("INSTAGRAM_APP_ID",    "INSTAGRAM_APP_ID"),
    "facebook":       ("FACEBOOK_APP_ID",     "FACEBOOK_APP_ID"),
    "youtube":        ("YOUTUBE_CLIENT_ID",   "YOUTUBE_CLIENT_ID"),
    "linkedin":       ("LINKEDIN_CLIENT_ID",  "LINKEDIN_CLIENT_ID"),
    "x":              ("TWITTER_API_KEY",     "TWITTER_API_KEY"),
}


def _require_credential(platform: str) -> str:
    """Return the credential value or raise a clear 422 if it is not configured."""
    settings = get_settings()
    attr, env_var = _PLATFORM_CREDS.get(platform, ("", ""))
    if not attr:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    value = getattr(settings, attr, "").strip()
    if not value:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{platform.title()} is not configured. "
                f"Set {env_var} in your backend/.env file and restart the server."
            ),
        )
    return value


def _build_oauth_url(platform: str) -> str:
    """
    Build the OAuth redirect URL for a given platform.
    Reads settings fresh via get_settings() (lru_cache — same object every call,
    but NOT cached at module-import time, so restarts always pick up new .env values).
    """
    settings = get_settings()

    if platform == "instagram":
        client_id = _require_credential("instagram")
        return (
            f"https://api.instagram.com/oauth/authorize?client_id={client_id}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/instagram/callback"
            "&scope=user_profile,user_media&response_type=code"
        )

    if platform == "facebook":
        client_id = _require_credential("facebook")
        return (
            f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/facebook/callback"
            "&scope=pages_manage_posts,pages_read_engagement,publish_video&response_type=code"
        )

    if platform == "youtube":
        client_id = _require_credential("youtube")
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/youtube/callback"
            "&scope=https://www.googleapis.com/auth/youtube.upload"
            "&response_type=code&access_type=offline"
        )

    if platform == "linkedin":
        client_id = _require_credential("linkedin")
        return (
            f"https://www.linkedin.com/oauth/v2/authorization?client_id={client_id}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/linkedin/callback"
            "&scope=ugcPost+w_member_social&response_type=code"
        )

    if platform == "x":
        client_id = _require_credential("x")
        return (
            f"https://twitter.com/i/oauth2/authorize?client_id={client_id}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/x/callback"
            "&scope=tweet.read+tweet.write+users.read&response_type=code"
            "&code_challenge=challenge&code_challenge_method=plain"
        )

    raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")


@router.get("/status")
async def platforms_status(_: CurrentUser) -> dict:
    """
    Returns which platforms have credentials configured.
    Useful for debugging missing OAuth config without exposing the actual keys.
    """
    settings = get_settings()
    return {
        "instagram": bool(settings.INSTAGRAM_APP_ID.strip()),
        "facebook":  bool(settings.FACEBOOK_APP_ID.strip()),
        "youtube":   bool(settings.YOUTUBE_CLIENT_ID.strip()),
        "linkedin":  bool(settings.LINKEDIN_CLIENT_ID.strip()),
        "x":         bool(settings.TWITTER_API_KEY.strip()),
    }


@router.get("/{platform}/oauth-url")
async def get_oauth_url(platform: str, _: CurrentUser) -> dict:
    url = _build_oauth_url(platform)
    return {"url": url, "platform": platform}


@router.get("/{platform}/callback")
async def platform_callback(
    platform: str, code: str = "", state: str = ""
) -> HTMLResponse:
    html = f"""<html><body><p>Connecting {platform}...</p>
    <script>
        window.opener && window.opener.postMessage(
            {{type:'oauth_success',platform:'{platform}',code:'{code}'}},
            window.location.origin
        );
        window.close();
    </script></body></html>"""
    return HTMLResponse(html)


@router.delete("/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    current_user: CurrentUser,
    auth_service: AuthSvc,
    db: DbSession,
) -> dict:
    auth_service.remove_platform_token(current_user, platform)
    await db.flush()
    await db.commit()
    return {"message": f"Disconnected from {platform}"}
