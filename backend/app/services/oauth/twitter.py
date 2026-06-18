"""Twitter OAuth service implementation."""
from __future__ import annotations

import os
from typing import Dict, Any

from .base import BaseOAuthService, OAuthError
from app.core.logging import get_logger

log = get_logger(__name__)


class TwitterOAuth(BaseOAuthService):
    """Twitter OAuth service using Twitter API v2."""
    
    @property
    def platform_name(self) -> str:
        return "Twitter"
    
    @property
    def platform_key(self) -> str:
        return "twitter"
    
    @property
    def client_id(self) -> str:
        return os.getenv("TWITTER_CLIENT_ID", "")
    
    @property
    def client_secret(self) -> str:
        return os.getenv("TWITTER_CLIENT_SECRET", "")
    
    @property
    def authorization_url(self) -> str:
        return "https://twitter.com/i/oauth2/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://api.twitter.com/2/oauth2/token"
    
    @property
    def required_scopes(self) -> list[str]:
        return [
            "tweet.read",
            "tweet.write", 
            "users.read",
            "follows.read",
            "offline.access"  # Required for refresh token
        ]
    
    @property
    def supports_publishing(self) -> bool:
        return True
    
    @property
    def supports_analytics(self) -> bool:
        return True
    
    def _get_auth_params(self, code_verifier: str | None = None) -> Dict[str, str]:
        """Twitter requires PKCE; rely on the base class for S256 challenge.

        If the caller did not supply a verifier we leave the PKCE fields blank
        and Twitter will reject the request, surfacing the misconfiguration
        instead of silently shipping a hardcoded challenge to production.
        """
        return {"response_type": "code"}
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get Twitter user profile."""
        try:
            # Get user info
            user_data = await self._make_api_request(
                "GET",
                "https://api.twitter.com/2/users/me",
                access_token,
                params={
                    "user.fields": "id,name,username,description,profile_image_url,public_metrics,verified,url"
                }
            )
            
            user = user_data.get("data", {})
            metrics = user.get("public_metrics", {})
            
            return {
                "id": user.get("id"),
                "username": user.get("username"),
                "display_name": user.get("name"),
                "avatar_url": user.get("profile_image_url", "").replace("_normal", "_400x400"),  # Get higher res
                "profile_url": f"https://twitter.com/{user.get('username', '')}" if user.get("username") else None,
                "followers_count": metrics.get("followers_count", 0),
                "following_count": metrics.get("following_count", 0),
                "posts_count": metrics.get("tweet_count", 0),
                "description": user.get("description", ""),
                "verified": user.get("verified", False),
                "website": user.get("url"),
            }
            
        except Exception as e:
            log.error("twitter.profile.failed", error=str(e))
            raise OAuthError(f"Failed to get Twitter profile: {str(e)}")
    
    async def get_user_tweets(self, access_token: str, limit: int = 25) -> list[Dict[str, Any]]:
        """Get user's tweets."""
        try:
            # First get user ID
            user_data = await self._make_api_request(
                "GET",
                "https://api.twitter.com/2/users/me",
                access_token
            )
            user_id = user_data["data"]["id"]
            
            # Get user tweets
            tweets_data = await self._make_api_request(
                "GET",
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                access_token,
                params={
                    "tweet.fields": "id,text,created_at,public_metrics,attachments,context_annotations",
                    "max_results": min(limit, 100),  # Twitter API limit
                    "exclude": "retweets,replies"
                }
            )
            
            tweets = []
            for tweet in tweets_data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "url": f"https://twitter.com/i/status/{tweet.get('id')}",
                    "retweet_count": metrics.get("retweet_count", 0),
                    "like_count": metrics.get("like_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "quote_count": metrics.get("quote_count", 0),
                    "impression_count": metrics.get("impression_count", 0),
                })
            
            return tweets
            
        except Exception as e:
            log.error("twitter.tweets.failed", error=str(e))
            raise OAuthError(f"Failed to get Twitter tweets: {str(e)}")
    
    async def get_tweet_analytics(self, access_token: str, tweet_id: str) -> Dict[str, Any]:
        """Get analytics for a specific tweet."""
        try:
            tweet_data = await self._make_api_request(
                "GET",
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                access_token,
                params={
                    "tweet.fields": "public_metrics,non_public_metrics,organic_metrics"
                }
            )
            
            tweet = tweet_data.get("data", {})
            public_metrics = tweet.get("public_metrics", {})
            organic_metrics = tweet.get("organic_metrics", {})
            
            return {
                "impressions": organic_metrics.get("impression_count", public_metrics.get("impression_count", 0)),
                "engagements": organic_metrics.get("user_profile_clicks", 0),
                "likes": public_metrics.get("like_count", 0),
                "retweets": public_metrics.get("retweet_count", 0),
                "replies": public_metrics.get("reply_count", 0),
                "quotes": public_metrics.get("quote_count", 0),
                "url_clicks": organic_metrics.get("url_link_clicks", 0),
                "hashtag_clicks": organic_metrics.get("hashtag_clicks", 0),
                "detail_expands": organic_metrics.get("detail_expands", 0),
            }
            
        except Exception as e:
            log.error("twitter.analytics.failed", tweet_id=tweet_id, error=str(e))
            raise OAuthError(f"Failed to get Twitter analytics: {str(e)}")
    
    async def post_tweet(
        self, 
        access_token: str, 
        text: str,
        media_ids: list[str] = None,
        reply_to: str = None
    ) -> Dict[str, Any]:
        """Post a tweet."""
        try:
            tweet_data = {
                "text": text
            }
            
            if media_ids:
                tweet_data["media"] = {"media_ids": media_ids}
            
            if reply_to:
                tweet_data["reply"] = {"in_reply_to_tweet_id": reply_to}
            
            response = await self._make_api_request(
                "POST",
                "https://api.twitter.com/2/tweets",
                access_token,
                json=tweet_data
            )
            
            tweet = response.get("data", {})
            
            return {
                "tweet_id": tweet.get("id"),
                "text": tweet.get("text"),
                "url": f"https://twitter.com/i/status/{tweet.get('id')}",
            }
            
        except Exception as e:
            log.error("twitter.post.failed", error=str(e))
            raise OAuthError(f"Failed to post tweet: {str(e)}")
    
    async def upload_media(self, access_token: str, media_data: bytes, media_type: str) -> str:
        """Upload media to Twitter."""
        try:
            # Twitter uses a different endpoint for media upload
            # This is a simplified version - real implementation would use chunked upload for large files
            
            files = {"media": (f"media.{media_type.split('/')[-1]}", media_data, media_type)}
            
            response = await self.client.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                headers={"Authorization": f"Bearer {access_token}"},
                files=files
            )
            response.raise_for_status()
            
            media_response = response.json()
            return media_response["media_id_string"]
            
        except Exception as e:
            log.error("twitter.media_upload.failed", error=str(e))
            raise OAuthError(f"Failed to upload Twitter media: {str(e)}")
    
    def _supports_refresh(self) -> bool:
        """Twitter OAuth 2.0 supports token refresh."""
        return True
    
    async def revoke_token(self, access_token: str) -> None:
        """Revoke Twitter OAuth token."""
        try:
            await self._make_api_request(
                "POST",
                "https://api.twitter.com/2/oauth2/revoke",
                access_token,
                data={
                    "token": access_token,
                    "client_id": self.client_id
                }
            )
            log.info("twitter.revoke.success")
        except Exception as e:
            log.error("twitter.revoke.failed", error=str(e))
            raise OAuthError(f"Failed to revoke Twitter token: {str(e)}")