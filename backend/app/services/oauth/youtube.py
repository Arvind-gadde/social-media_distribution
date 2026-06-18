"""YouTube OAuth service implementation."""
from __future__ import annotations

import os
from typing import Dict, Any

from .base import BaseOAuthService, OAuthError
from app.core.logging import get_logger

log = get_logger(__name__)


class YouTubeOAuth(BaseOAuthService):
    """YouTube OAuth service using Google OAuth 2.0."""
    
    @property
    def platform_name(self) -> str:
        return "YouTube"
    
    @property
    def platform_key(self) -> str:
        return "youtube"
    
    @property
    def client_id(self) -> str:
        return os.getenv("GOOGLE_CLIENT_ID", "")
    
    @property
    def client_secret(self) -> str:
        return os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    @property
    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"
    
    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"
    
    @property
    def required_scopes(self) -> list[str]:
        return [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/youtubepartner",
        ]
    
    @property
    def supports_publishing(self) -> bool:
        return True
    
    @property
    def supports_analytics(self) -> bool:
        return True
    
    def _get_auth_params(self, code_verifier: str | None = None) -> Dict[str, str]:
        """Google-specific authorization parameters."""
        return {
            "access_type": "offline",  # Required for refresh token
            "prompt": "consent",       # Force consent screen to get refresh token
        }
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get YouTube channel information."""
        try:
            # Get channel info
            channel_data = await self._make_api_request(
                "GET",
                "https://www.googleapis.com/youtube/v3/channels",
                access_token,
                params={
                    "part": "snippet,statistics,brandingSettings",
                    "mine": "true"
                }
            )
            
            if not channel_data.get("items"):
                raise OAuthError("No YouTube channel found for this account")
            
            channel = channel_data["items"][0]
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            
            return {
                "id": channel["id"],
                "username": snippet.get("customUrl", "").replace("@", "") if snippet.get("customUrl") else None,
                "display_name": snippet.get("title"),
                "avatar_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "profile_url": f"https://youtube.com/channel/{channel['id']}",
                "followers_count": int(statistics.get("subscriberCount", 0)),
                "following_count": 0,  # YouTube doesn't have following count
                "posts_count": int(statistics.get("videoCount", 0)),
                "description": snippet.get("description", ""),
                "country": snippet.get("country"),
                "view_count": int(statistics.get("viewCount", 0)),
            }
            
        except Exception as e:
            log.error("youtube.profile.failed", error=str(e))
            raise OAuthError(f"Failed to get YouTube profile: {str(e)}")
    
    async def get_channel_videos(self, access_token: str, limit: int = 25) -> list[Dict[str, Any]]:
        """Get channel's videos."""
        try:
            # First get the uploads playlist ID
            channel_data = await self._make_api_request(
                "GET",
                "https://www.googleapis.com/youtube/v3/channels",
                access_token,
                params={
                    "part": "contentDetails",
                    "mine": "true"
                }
            )
            
            if not channel_data.get("items"):
                return []
            
            uploads_playlist_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from uploads playlist
            playlist_data = await self._make_api_request(
                "GET",
                "https://www.googleapis.com/youtube/v3/playlistItems",
                access_token,
                params={
                    "part": "snippet,contentDetails",
                    "playlistId": uploads_playlist_id,
                    "maxResults": limit
                }
            )
            
            videos = []
            for item in playlist_data.get("items", []):
                snippet = item.get("snippet", {})
                videos.append({
                    "id": snippet.get("resourceId", {}).get("videoId"),
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "published_at": snippet.get("publishedAt"),
                    "url": f"https://youtube.com/watch?v={snippet.get('resourceId', {}).get('videoId')}",
                })
            
            return videos
            
        except Exception as e:
            log.error("youtube.videos.failed", error=str(e))
            raise OAuthError(f"Failed to get YouTube videos: {str(e)}")
    
    async def get_video_analytics(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Get analytics for a specific video."""
        try:
            # Get video statistics
            video_data = await self._make_api_request(
                "GET",
                "https://www.googleapis.com/youtube/v3/videos",
                access_token,
                params={
                    "part": "statistics",
                    "id": video_id
                }
            )
            
            if not video_data.get("items"):
                return {}
            
            stats = video_data["items"][0].get("statistics", {})
            
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,  # Not available in public API
                "watch_time": 0,  # Requires YouTube Analytics API
                "impressions": 0,  # Requires YouTube Analytics API
                "ctr": 0,  # Requires YouTube Analytics API
            }
            
        except Exception as e:
            log.error("youtube.analytics.failed", video_id=video_id, error=str(e))
            raise OAuthError(f"Failed to get YouTube analytics: {str(e)}")
    
    async def upload_video(
        self, 
        access_token: str, 
        video_file: bytes, 
        title: str,
        description: str = "",
        tags: list[str] = None,
        privacy_status: str = "private"
    ) -> Dict[str, Any]:
        """Upload a video to YouTube."""
        try:
            # Prepare metadata
            metadata = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Upload video (simplified - real implementation would use resumable upload)
            response = await self._make_api_request(
                "POST",
                "https://www.googleapis.com/upload/youtube/v3/videos",
                access_token,
                params={
                    "part": "snippet,status",
                    "uploadType": "multipart"
                },
                json=metadata
            )
            
            return {
                "video_id": response["id"],
                "url": f"https://youtube.com/watch?v={response['id']}",
                "title": response["snippet"]["title"],
                "status": response["status"]["privacyStatus"]
            }
            
        except Exception as e:
            log.error("youtube.upload.failed", error=str(e))
            raise OAuthError(f"Failed to upload YouTube video: {str(e)}")
    
    async def revoke_token(self, access_token: str) -> None:
        """Revoke Google OAuth token."""
        try:
            await self.client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token}
            )
            log.info("youtube.revoke.success")
        except Exception as e:
            log.error("youtube.revoke.failed", error=str(e))
            raise OAuthError(f"Failed to revoke YouTube token: {str(e)}")