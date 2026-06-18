"""TikTok OAuth service implementation."""
from __future__ import annotations

import os
from typing import Dict, Any

from .base import BaseOAuthService, OAuthError
from app.core.logging import get_logger

log = get_logger(__name__)


class TikTokOAuth(BaseOAuthService):
    """TikTok OAuth service using TikTok for Developers API."""
    
    @property
    def platform_name(self) -> str:
        return "TikTok"
    
    @property
    def platform_key(self) -> str:
        return "tiktok"
    
    @property
    def client_id(self) -> str:
        return os.getenv("TIKTOK_CLIENT_ID", "")
    
    @property
    def client_secret(self) -> str:
        return os.getenv("TIKTOK_CLIENT_SECRET", "")
    
    @property
    def authorization_url(self) -> str:
        return "https://www.tiktok.com/v2/auth/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://open.tiktokapis.com/v2/oauth/token"
    
    @property
    def required_scopes(self) -> list[str]:
        return [
            "user.info.basic",
            "user.info.profile",
            "user.info.stats",
            "video.list",
            "video.publish",
        ]
    
    @property
    def supports_publishing(self) -> bool:
        return True
    
    @property
    def supports_analytics(self) -> bool:
        return True
    
    def _get_auth_params(self, code_verifier: str | None = None) -> Dict[str, str]:
        """TikTok-specific authorization parameters."""
        return {
            "response_type": "code",
        }
    
    def _get_token_params(self) -> Dict[str, str]:
        """TikTok-specific token exchange parameters."""
        return {}
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get TikTok user profile."""
        try:
            # Get user info
            user_data = await self._make_api_request(
                "POST",
                "https://open.tiktokapis.com/v2/user/info/",
                access_token,
                json={
                    "fields": [
                        "open_id",
                        "union_id", 
                        "avatar_url",
                        "display_name",
                        "username",
                        "follower_count",
                        "following_count",
                        "likes_count",
                        "video_count"
                    ]
                }
            )
            
            user = user_data.get("data", {}).get("user", {})
            
            return {
                "id": user.get("open_id"),
                "username": user.get("username"),
                "display_name": user.get("display_name"),
                "avatar_url": user.get("avatar_url"),
                "profile_url": f"https://tiktok.com/@{user.get('username', '')}" if user.get("username") else None,
                "followers_count": user.get("follower_count", 0),
                "following_count": user.get("following_count", 0),
                "posts_count": user.get("video_count", 0),
                "likes_count": user.get("likes_count", 0),
            }
            
        except Exception as e:
            log.error("tiktok.profile.failed", error=str(e))
            raise OAuthError(f"Failed to get TikTok profile: {str(e)}")
    
    async def get_user_videos(self, access_token: str, limit: int = 20) -> list[Dict[str, Any]]:
        """Get user's TikTok videos."""
        try:
            video_data = await self._make_api_request(
                "POST",
                "https://open.tiktokapis.com/v2/video/list/",
                access_token,
                json={
                    "fields": [
                        "id",
                        "title",
                        "video_description",
                        "duration",
                        "cover_image_url",
                        "share_url",
                        "view_count",
                        "like_count",
                        "comment_count",
                        "share_count",
                        "create_time"
                    ],
                    "max_count": limit
                }
            )
            
            videos = []
            for video in video_data.get("data", {}).get("videos", []):
                videos.append({
                    "id": video.get("id"),
                    "title": video.get("title", ""),
                    "description": video.get("video_description", ""),
                    "thumbnail_url": video.get("cover_image_url"),
                    "duration": video.get("duration"),
                    "url": video.get("share_url"),
                    "view_count": video.get("view_count", 0),
                    "like_count": video.get("like_count", 0),
                    "comment_count": video.get("comment_count", 0),
                    "share_count": video.get("share_count", 0),
                    "created_at": video.get("create_time"),
                })
            
            return videos
            
        except Exception as e:
            log.error("tiktok.videos.failed", error=str(e))
            raise OAuthError(f"Failed to get TikTok videos: {str(e)}")
    
    async def get_video_analytics(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """Get analytics for a specific TikTok video."""
        try:
            # TikTok analytics are included in the video list response
            # This is a placeholder for more detailed analytics
            return {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "profile_views": 0,
                "reach": 0,
                "engagement_rate": 0,
            }
            
        except Exception as e:
            log.error("tiktok.analytics.failed", video_id=video_id, error=str(e))
            raise OAuthError(f"Failed to get TikTok analytics: {str(e)}")
    
    async def upload_video(
        self, 
        access_token: str, 
        video_file: bytes, 
        title: str = "",
        description: str = "",
        privacy_level: str = "SELF_ONLY"
    ) -> Dict[str, Any]:
        """Upload a video to TikTok."""
        try:
            # Step 1: Initialize upload
            init_response = await self._make_api_request(
                "POST",
                "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                access_token,
                json={
                    "post_info": {
                        "title": title,
                        "description": description,
                        "privacy_level": privacy_level,
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                        "video_cover_timestamp_ms": 1000
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": len(video_file),
                        "chunk_size": len(video_file),
                        "total_chunk_count": 1
                    }
                }
            )
            
            publish_id = init_response["data"]["publish_id"]
            upload_url = init_response["data"]["upload_url"]
            
            # Step 2: Upload video file
            upload_response = await self.client.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes 0-{len(video_file)-1}/{len(video_file)}",
                    "Content-Length": str(len(video_file))
                },
                content=video_file
            )
            upload_response.raise_for_status()
            
            # Step 3: Confirm upload
            confirm_response = await self._make_api_request(
                "POST",
                "https://open.tiktokapis.com/v2/post/publish/",
                access_token,
                json={"publish_id": publish_id}
            )
            
            return {
                "publish_id": publish_id,
                "status": confirm_response["data"]["status"],
                "message": "Video uploaded successfully"
            }
            
        except Exception as e:
            log.error("tiktok.upload.failed", error=str(e))
            raise OAuthError(f"Failed to upload TikTok video: {str(e)}")
    
    def _supports_refresh(self) -> bool:
        """TikTok supports token refresh."""
        return True
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh TikTok access token."""
        data = {
            "client_key": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        
        try:
            response = await self.client.post(
                self.token_url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            return self._normalize_token_response(token_data["data"])
            
        except Exception as e:
            log.error("tiktok.refresh.failed", error=str(e))
            raise OAuthError(f"TikTok token refresh failed: {str(e)}")
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for TikTok tokens."""
        data = {
            "client_key": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = await self.client.post(
                self.token_url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            return self._normalize_token_response(token_data["data"])
            
        except Exception as e:
            log.error("tiktok.code_exchange.failed", error=str(e))
            raise OAuthError(f"TikTok code exchange failed: {str(e)}")