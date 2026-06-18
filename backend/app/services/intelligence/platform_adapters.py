"""Platform API adapters for trend fetching."""
from typing import Any
from uuid import UUID

import httpx

from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class TikTokTrendAdapter:
    """Fetch trending content from TikTok."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'TIKTOK_API_KEY', None)
    
    async def fetch_trends(self, niche_keywords: list[str]) -> list[dict[str, Any]]:
        """Fetch TikTok trends using RapidAPI TikTok endpoint."""
        if not self.api_key:
            logger.warning("tiktok_api_key_missing")
            return []
        
        trends = []
        
        async with httpx.AsyncClient() as client:
            # Using RapidAPI TikTok endpoint as example
            url = "https://tiktok-scraper7.p.rapidapi.com/feed/search"
            
            for keyword in niche_keywords[:3]:  # Limit to avoid costs
                params = {"keywords": keyword, "count": 10}
                headers = {
                    "X-RapidAPI-Key": self.api_key,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                }
                
                try:
                    response = await client.get(url, params=params, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        video = item.get("video", {})
                        stats = item.get("stats", {})
                        
                        trends.append({
                            "title": item.get("desc", "")[:200],
                            "platform": "tiktok",
                            "type": "video",
                            "score": self._calculate_score(stats),
                            "description": item.get("desc", ""),
                            "hashtags": [tag.get("name") for tag in item.get("textExtra", [])],
                            "example_urls": [f"https://tiktok.com/@{item.get('author', {}).get('uniqueId')}/video/{item.get('id')}"],
                            "source": "tiktok_rapidapi",
                        })
                    
                except Exception as e:
                    logger.error("tiktok_trends_fetch_failed", keyword=keyword, error=str(e))
        
        logger.info("tiktok_trends_fetched", count=len(trends), keywords=niche_keywords)
        return trends
    
    def _calculate_score(self, stats: dict) -> float:
        """Calculate trend score from TikTok statistics."""
        plays = stats.get("playCount", 0)
        likes = stats.get("diggCount", 0)
        shares = stats.get("shareCount", 0)
        
        score = min(100.0, (plays / 10000) + (likes / 1000) + (shares / 100))
        return round(score, 2)


class YouTubeTrendAdapter:
    """Fetch trending videos from YouTube."""
    
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
    
    async def fetch_trends(
        self,
        niche_keywords: list[str],
        region_code: str = "IN",
    ) -> list[dict[str, Any]]:
        """Fetch YouTube trending videos.
        
        Uses YouTube Data API v3.
        """
        if not self.api_key:
            logger.warning("youtube_api_key_missing")
            return []
        
        trends = []
        
        async with httpx.AsyncClient() as client:
            # Fetch trending videos
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "regionCode": region_code,
                "maxResults": 50,
                "key": self.api_key,
            }
            
            try:
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    
                    # Filter by niche keywords
                    title = snippet.get("title", "").lower()
                    description = snippet.get("description", "").lower()
                    
                    if any(kw.lower() in title or kw.lower() in description for kw in niche_keywords):
                        trends.append({
                            "title": snippet.get("title"),
                            "platform": "youtube",
                            "type": "topic",
                            "score": self._calculate_score(stats),
                            "description": snippet.get("description", "")[:500],
                            "hashtags": snippet.get("tags", [])[:10],
                            "example_urls": [f"https://youtube.com/watch?v={item['id']}"],
                            "source": "youtube_trending_api",
                        })
                
                logger.info("youtube_trends_fetched", count=len(trends))
                
            except Exception as e:
                logger.error("youtube_trends_fetch_failed", error=str(e))
        
        return trends
    
    def _calculate_score(self, stats: dict) -> float:
        """Calculate trend score from YouTube statistics."""
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        
        # Simple scoring: normalize to 0-100
        engagement = likes + (comments * 2)
        score = min(100.0, (views / 100000) + (engagement / 1000))
        return round(score, 2)


class TwitterTrendAdapter:
    """Fetch trending topics from Twitter/X."""
    
    def __init__(self):
        self.bearer_token = getattr(settings, 'TWITTER_BEARER_TOKEN', None)
    
    async def fetch_trends(
        self,
        niche_keywords: list[str],
        woeid: int = 23424848,  # India
    ) -> list[dict[str, Any]]:
        """Fetch Twitter trending topics using API v2."""
        if not self.bearer_token:
            logger.warning("twitter_bearer_token_missing")
            return []
        
        trends = []
        
        async with httpx.AsyncClient() as client:
            # Twitter API v2 doesn't have direct trending endpoint
            # Use search recent tweets for niche keywords
            url = "https://api.twitter.com/2/tweets/search/recent"
            
            for keyword in niche_keywords[:5]:  # Limit to avoid rate limits
                params = {
                    "query": f"{keyword} -is:retweet lang:en",
                    "max_results": 10,
                    "tweet.fields": "public_metrics,created_at",
                }
                headers = {"Authorization": f"Bearer {self.bearer_token}"}
                
                try:
                    response = await client.get(url, params=params, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    for tweet in data.get("data", []):
                        metrics = tweet.get("public_metrics", {})
                        trends.append({
                            "title": tweet.get("text", "")[:200],
                            "platform": "twitter",
                            "type": "topic",
                            "score": self._calculate_score(metrics),
                            "description": tweet.get("text", ""),
                            "hashtags": [],
                            "example_urls": [f"https://twitter.com/i/web/status/{tweet['id']}"],
                            "source": "twitter_search_api",
                        })
                    
                except Exception as e:
                    logger.error("twitter_trends_fetch_failed", keyword=keyword, error=str(e))
        
        logger.info("twitter_trends_fetched", count=len(trends))
        return trends
    
    def _calculate_score(self, metrics: dict) -> float:
        """Calculate trend score from Twitter metrics."""
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        
        score = min(100.0, (likes / 100) + (retweets * 2 / 100) + (replies / 50))
        return round(score, 2)


class InstagramTrendAdapter:
    """Fetch trending content from Instagram."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'INSTAGRAM_RAPIDAPI_KEY', None)
    
    async def fetch_trends(self, niche_keywords: list[str]) -> list[dict[str, Any]]:
        """Fetch Instagram trending hashtags using RapidAPI."""
        if not self.api_key:
            logger.warning("instagram_api_key_missing")
            return []
        
        trends = []
        
        async with httpx.AsyncClient() as client:
            # Using RapidAPI Instagram endpoint
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/hashtag"
            
            for keyword in niche_keywords[:3]:  # Limit to avoid costs
                params = {"hashtag": keyword}
                headers = {
                    "X-RapidAPI-Key": self.api_key,
                    "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
                }
                
                try:
                    response = await client.get(url, params=params, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    hashtag_data = data.get("data", {}).get("hashtag", {})
                    if hashtag_data:
                        trends.append({
                            "title": f"#{hashtag_data.get('name', keyword)}",
                            "platform": "instagram",
                            "type": "hashtag",
                            "score": self._calculate_score(hashtag_data),
                            "description": f"Trending hashtag with {hashtag_data.get('media_count', 0)} posts",
                            "hashtags": [hashtag_data.get('name', keyword)],
                            "example_urls": [f"https://instagram.com/explore/tags/{keyword}"],
                            "source": "instagram_rapidapi",
                        })
                    
                except Exception as e:
                    logger.error("instagram_trends_fetch_failed", keyword=keyword, error=str(e))
        
        logger.info("instagram_trends_fetched", count=len(trends), keywords=niche_keywords)
        return trends
    
    def _calculate_score(self, hashtag_data: dict) -> float:
        """Calculate trend score from Instagram hashtag data."""
        media_count = hashtag_data.get("media_count", 0)
        
        # Normalize to 0-100 based on post count
        score = min(100.0, media_count / 10000)
        return round(score, 2)


class RedditTrendAdapter:
    """Fetch rising posts from Reddit."""
    
    async def fetch_trends(
        self,
        niche_keywords: list[str],
        subreddits: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch Reddit rising posts.
        
        Uses Reddit API (no auth required for public data).
        """
        trends = []
        
        if not subreddits:
            # Default subreddits based on niche
            subreddits = ["all"]
        
        async with httpx.AsyncClient() as client:
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/rising.json"
                params = {"limit": 25}
                
                try:
                    response = await client.get(
                        url,
                        params=params,
                        headers={"User-Agent": "ContentFlow/1.0"},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for post in data.get("data", {}).get("children", []):
                        post_data = post.get("data", {})
                        title = post_data.get("title", "").lower()
                        
                        # Filter by niche keywords
                        if any(kw.lower() in title for kw in niche_keywords):
                            trends.append({
                                "title": post_data.get("title"),
                                "platform": "reddit",
                                "type": "topic",
                                "score": self._calculate_score(post_data),
                                "description": post_data.get("selftext", "")[:500],
                                "hashtags": [],
                                "example_urls": [f"https://reddit.com{post_data.get('permalink')}"],
                                "source": f"reddit_r_{subreddit}",
                            })
                    
                except Exception as e:
                    logger.error(
                        "reddit_trends_fetch_failed",
                        subreddit=subreddit,
                        error=str(e),
                    )
        
        logger.info("reddit_trends_fetched", count=len(trends))
        return trends
    
    def _calculate_score(self, post_data: dict) -> float:
        """Calculate trend score from Reddit post data."""
        score = post_data.get("score", 0)
        num_comments = post_data.get("num_comments", 0)
        
        # Simple scoring: normalize to 0-100
        trend_score = min(100.0, (score / 100) + (num_comments / 10))
        return round(trend_score, 2)


async def fetch_all_trends(
    niche_id: UUID,
    niche_keywords: list[str],
) -> list[dict[str, Any]]:
    """Fetch trends from all platforms for a niche.
    
    Args:
        niche_id: Niche UUID
        niche_keywords: Keywords to filter trends
        
    Returns:
        Combined list of trends from all platforms
    """
    all_trends = []
    
    # YouTube (has real implementation)
    youtube = YouTubeTrendAdapter()
    youtube_trends = await youtube.fetch_trends(niche_keywords)
    all_trends.extend(youtube_trends)
    
    # Reddit (has real implementation)
    reddit = RedditTrendAdapter()
    reddit_trends = await reddit.fetch_trends(niche_keywords)
    all_trends.extend(reddit_trends)
    
    # TikTok (placeholder)
    tiktok = TikTokTrendAdapter()
    tiktok_trends = await tiktok.fetch_trends(niche_keywords)
    all_trends.extend(tiktok_trends)
    
    # Twitter (placeholder)
    twitter = TwitterTrendAdapter()
    twitter_trends = await twitter.fetch_trends(niche_keywords)
    all_trends.extend(twitter_trends)
    
    # Instagram (placeholder)
    instagram = InstagramTrendAdapter()
    instagram_trends = await instagram.fetch_trends(niche_keywords)
    all_trends.extend(instagram_trends)
    
    logger.info(
        "all_trends_fetched",
        niche_id=str(niche_id),
        total_trends=len(all_trends),
    )
    
    return all_trends
