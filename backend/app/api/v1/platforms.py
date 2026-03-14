"""Platform OAuth connection routes."""
from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.api.deps import CurrentUser, AuthSvc, DbSession
from app.config import get_settings
from app.core.security import generate_oauth_state

router = APIRouter(prefix="/platforms", tags=["platforms"])
settings = get_settings()


def _build_oauth_urls() -> dict[str, str]:
    return {
        "instagram": (
            f"https://api.instagram.com/oauth/authorize?client_id={settings.INSTAGRAM_APP_ID}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/instagram/callback"
            "&scope=user_profile,user_media&response_type=code"
        ),
        "facebook": (
            f"https://www.facebook.com/v19.0/dialog/oauth?client_id={settings.FACEBOOK_APP_ID}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/facebook/callback"
            "&scope=pages_manage_posts,pages_read_engagement,publish_video&response_type=code"
        ),
        "youtube": (
            f"https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.YOUTUBE_CLIENT_ID}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/youtube/callback"
            "&scope=https://www.googleapis.com/auth/youtube.upload&response_type=code&access_type=offline"
        ),
        "linkedin": (
            f"https://www.linkedin.com/oauth/v2/authorization?client_id={settings.LINKEDIN_CLIENT_ID}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/linkedin/callback"
            "&scope=ugcPost+w_member_social&response_type=code"
        ),
        "x": (
            f"https://twitter.com/i/oauth2/authorize?client_id={settings.TWITTER_API_KEY}"
            "&redirect_uri=http://localhost:8000/api/v1/platforms/x/callback"
            "&scope=tweet.read+tweet.write+users.read&response_type=code"
            "&code_challenge=challenge&code_challenge_method=plain"
        ),
    }


@router.get("/{platform}/oauth-url")
async def get_oauth_url(platform: str, _: CurrentUser) -> dict:
    from app.exceptions import NotFoundError
    urls = _build_oauth_urls()
    url = urls.get(platform)
    if not url:
        raise NotFoundError("OAuth config", platform)
    return {"url": url, "platform": platform}


@router.get("/{platform}/callback")
async def platform_callback(platform: str, code: str = "", state: str = "") -> HTMLResponse:
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
    platform: str, current_user: CurrentUser,
    auth_service: AuthSvc, db: DbSession,
) -> dict:
    auth_service.remove_platform_token(current_user, platform)
    await db.flush()
    await db.commit()
    return {"message": f"Disconnected from {platform}"}
