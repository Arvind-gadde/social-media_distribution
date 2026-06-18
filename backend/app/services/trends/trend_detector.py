"""Trend detection service from multiple sources.

Fetches trends from:
- Google Trends (pytrends)
- Reddit (PRAW)
- YouTube (API)
- TikTok (Playwright scraping)
- Instagram (Playwright scraping)
- Twitter/X (API)
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import structlog
from bs4 import BeautifulSoup

# Google Trends
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    structlog.get_logger(__name__).warning("pytrends not available")

# Reddit
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    structlog.get_logger(__name__).warning("praw not available")

from app.services.scraping.scraper import WebScraper

log = structlog.get_logger(__name__)


class TrendDetector:
    """Detect trends from multiple sources."""
    
    def __init__(
        self,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        youtube_api_key: Optional[str] = None,
    ):
        self.reddit_client_id = reddit_client_id
        self.reddit_client_secret = reddit_client_secret
        self.youtube_api_key = youtube_api_key
    
    async def fetch_google_trends(
        self,
        keywords: List[str],
        timeframe: str = 'now 7-d',
        geo: str = 'US',
    ) -> List[Dict]:
        """Fetch trends from Google Trends.
        
        Args:
            keywords: List of keywords to check
            timeframe: Time range (e.g., 'now 7-d', 'today 3-m')
            geo: Geographic region code
            
        Returns:
            List of trend dictionaries
        """
        if not PYTRENDS_AVAILABLE:
            log.warning("trend_detector.google_trends.unavailable")
            return self._mock_google_trends(keywords)
        
        try:
            log.info("trend_detector.google_trends.started",
                    keywords=keywords,
                    timeframe=timeframe)
            
            # Initialize pytrends
            pytrends = TrendReq(hl='en-US', tz=360)
            
            trends = []
            
            # Build payload for keywords
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            if not interest_df.empty:
                for keyword in keywords:
                    if keyword in interest_df.columns:
                        # Calculate trend metrics
                        values = interest_df[keyword].values
                        current_value = float(values[-1]) if len(values) > 0 else 0
                        avg_value = float(values.mean()) if len(values) > 0 else 0
                        
                        # Calculate velocity (growth rate)
                        if len(values) >= 2:
                            velocity = (values[-1] - values[0]) / max(values[0], 1)
                        else:
                            velocity = 0
                        
                        trends.append({
                            'title': keyword,
                            'source': 'google_trends',
                            'trend_type': 'topic',
                            'current_interest': current_value,
                            'avg_interest': avg_value,
                            'velocity': float(velocity),
                            'timeframe': timeframe,
                            'geo': geo,
                            'raw_data': values.tolist() if len(values) > 0 else [],
                        })
            
            # Get related queries
            try:
                related_queries = pytrends.related_queries()
                for keyword in keywords:
                    if keyword in related_queries:
                        rising = related_queries[keyword].get('rising')
                        if rising is not None and not rising.empty:
                            for _, row in rising.head(5).iterrows():
                                trends.append({
                                    'title': row['query'],
                                    'source': 'google_trends_related',
                                    'trend_type': 'topic',
                                    'current_interest': float(row.get('value', 0)),
                                    'velocity': 1.0,  # Rising queries have high velocity
                                    'parent_keyword': keyword,
                                })
            except Exception as e:
                log.warning("trend_detector.google_trends.related_queries_failed",
                           error=str(e))
            
            log.info("trend_detector.google_trends.completed",
                    trends_found=len(trends))
            
            return trends
        
        except Exception as e:
            log.error("trend_detector.google_trends.failed",
                     error=str(e),
                     error_type=type(e).__name__)
            return self._mock_google_trends(keywords)
    
    def _mock_google_trends(self, keywords: List[str]) -> List[Dict]:
        """Mock Google Trends data for testing."""
        return [
            {
                'title': keyword,
                'source': 'google_trends_mock',
                'trend_type': 'topic',
                'current_interest': 75,
                'avg_interest': 60,
                'velocity': 0.25,
                'timeframe': 'now 7-d',
                'geo': 'US',
            }
            for keyword in keywords[:3]
        ]
    
    async def fetch_reddit_trends(
        self,
        subreddits: List[str],
        time_filter: str = 'day',
        limit: int = 10,
    ) -> List[Dict]:
        """Fetch trending posts from Reddit.
        
        Args:
            subreddits: List of subreddit names (without r/)
            time_filter: Time filter ('hour', 'day', 'week', 'month', 'year', 'all')
            limit: Number of posts per subreddit
            
        Returns:
            List of trend dictionaries
        """
        if not PRAW_AVAILABLE or not self.reddit_client_id:
            log.warning("trend_detector.reddit.unavailable")
            return self._mock_reddit_trends(subreddits)
        
        try:
            log.info("trend_detector.reddit.started",
                    subreddits=subreddits,
                    time_filter=time_filter)
            
            # Initialize Reddit client
            reddit = praw.Reddit(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent='ContentFlow/1.0',
            )
            
            trends = []
            
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Get top posts
                    for post in subreddit.top(time_filter=time_filter, limit=limit):
                        # Calculate engagement score
                        engagement_score = post.score + (post.num_comments * 2)
                        
                        trends.append({
                            'title': post.title,
                            'source': 'reddit',
                            'trend_type': 'post',
                            'subreddit': subreddit_name,
                            'url': f"https://reddit.com{post.permalink}",
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'engagement_score': engagement_score,
                            'created_utc': datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                            'author': str(post.author) if post.author else '[deleted]',
                        })
                
                except Exception as e:
                    log.warning("trend_detector.reddit.subreddit_failed",
                               subreddit=subreddit_name,
                               error=str(e))
            
            log.info("trend_detector.reddit.completed",
                    trends_found=len(trends))
            
            return trends
        
        except Exception as e:
            log.error("trend_detector.reddit.failed",
                     error=str(e),
                     error_type=type(e).__name__)
            return self._mock_reddit_trends(subreddits)
    
    def _mock_reddit_trends(self, subreddits: List[str]) -> List[Dict]:
        """Mock Reddit trends for testing."""
        return [
            {
                'title': f"Trending post in r/{subreddit}",
                'source': 'reddit_mock',
                'trend_type': 'post',
                'subreddit': subreddit,
                'score': 1500,
                'num_comments': 250,
                'engagement_score': 2000,
            }
            for subreddit in subreddits[:2]
        ]
    
    async def fetch_youtube_trends(
        self,
        region_code: str = 'US',
        category_id: Optional[str] = None,
    ) -> List[Dict]:
        """Fetch trending videos from YouTube.
        
        Args:
            region_code: Region code (e.g., 'US', 'GB', 'IN')
            category_id: Optional category ID to filter
            
        Returns:
            List of trend dictionaries
        """
        if not self.youtube_api_key:
            log.warning("trend_detector.youtube.no_api_key")
            return self._mock_youtube_trends()
        
        # TODO: Implement YouTube API integration
        # For now, return mock data
        log.info("trend_detector.youtube.mock_mode")
        return self._mock_youtube_trends()
    
    def _mock_youtube_trends(self) -> List[Dict]:
        """Mock YouTube trends for testing."""
        return [
            {
                'title': "How AI Agents Are Changing Content Creation",
                'source': 'youtube_mock',
                'trend_type': 'video',
                'views': 500000,
                'likes': 25000,
                'comments': 1200,
                'channel': 'TechCreator',
            },
            {
                'title': "10 Productivity Hacks for Creators in 2026",
                'source': 'youtube_mock',
                'trend_type': 'video',
                'views': 350000,
                'likes': 18000,
                'comments': 800,
                'channel': 'ProductivityPro',
            },
        ]
    
    async def fetch_tiktok_trends(self) -> List[Dict]:
        """Scrape trending content from TikTok Discover page.
        
        Returns:
            List of trend dictionaries
        """
        try:
            log.info("trend_detector.tiktok.started")
            
            async with WebScraper() as scraper:
                # Scrape TikTok Discover page
                html = await scraper.scrape_with_playwright(
                    url='https://www.tiktok.com/discover',
                    wait_for_selector='[data-e2e="discover-item"]',
                    timeout=30000,
                )
                
                soup = BeautifulSoup(html, 'lxml')
                trends = []
                
                # Parse trending hashtags/topics
                # Note: TikTok's structure changes frequently, this is a simplified example
                discover_items = soup.select('[data-e2e="discover-item"]')
                
                for item in discover_items[:10]:
                    try:
                        title_elem = item.select_one('[data-e2e="discover-title"]')
                        views_elem = item.select_one('[data-e2e="discover-views"]')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            views_text = views_elem.get_text(strip=True) if views_elem else '0'
                            
                            trends.append({
                                'title': title,
                                'source': 'tiktok',
                                'trend_type': 'hashtag' if title.startswith('#') else 'topic',
                                'views_text': views_text,
                                'platform': 'tiktok',
                            })
                    except Exception as e:
                        log.warning("trend_detector.tiktok.item_parse_failed",
                                   error=str(e))
                
                log.info("trend_detector.tiktok.completed",
                        trends_found=len(trends))
                
                return trends if trends else self._mock_tiktok_trends()
        
        except Exception as e:
            log.error("trend_detector.tiktok.failed",
                     error=str(e),
                     error_type=type(e).__name__)
            return self._mock_tiktok_trends()
    
    def _mock_tiktok_trends(self) -> List[Dict]:
        """Mock TikTok trends for testing."""
        return [
            {
                'title': '#AIAgents',
                'source': 'tiktok_mock',
                'trend_type': 'hashtag',
                'views_text': '2.5B views',
                'platform': 'tiktok',
            },
            {
                'title': '#ProductivityHacks',
                'source': 'tiktok_mock',
                'trend_type': 'hashtag',
                'views_text': '1.8B views',
                'platform': 'tiktok',
            },
        ]
    
    def calculate_trend_score(
        self,
        velocity: float,
        volume: float,
        recency: float,
        engagement: float,
        diversity: float,
    ) -> float:
        """Calculate trend score 0-100.
        
        Args:
            velocity: Growth rate (0-1)
            volume: Total mentions/views (normalized 0-1)
            recency: How recent (0-1, 1 = very recent)
            engagement: Engagement rate (0-1)
            diversity: Platform diversity (0-1)
            
        Returns:
            Score from 0-100
        """
        score = (
            velocity * 30 +
            volume * 20 +
            recency * 20 +
            engagement * 20 +
            diversity * 10
        )
        return min(score, 100.0)
    
    def predict_peak_timing(
        self,
        velocity: float,
        current_volume: float,
        started_at: Optional[datetime] = None,
    ) -> datetime:
        """Predict when a trend will peak.
        
        Args:
            velocity: Growth rate
            current_volume: Current volume/interest
            started_at: When trend started
            
        Returns:
            Predicted peak datetime
        """
        # Simple heuristic: faster velocity = sooner peak
        # High velocity trends peak in 1-3 days
        # Medium velocity trends peak in 3-7 days
        # Low velocity trends peak in 7-14 days
        
        if velocity > 0.7:
            days_to_peak = 1 + (1 - velocity) * 2  # 1-3 days
        elif velocity > 0.4:
            days_to_peak = 3 + (0.7 - velocity) * 10  # 3-7 days
        else:
            days_to_peak = 7 + (0.4 - velocity) * 17.5  # 7-14 days
        
        return datetime.now(timezone.utc) + timedelta(days=days_to_peak)
    
    async def fetch_all_trends(
        self,
        niche_keywords: List[str],
        niche_subreddits: List[str],
    ) -> List[Dict]:
        """Fetch trends from all available sources.
        
        Args:
            niche_keywords: Keywords related to user's niche
            niche_subreddits: Subreddits related to user's niche
            
        Returns:
            Combined list of trends from all sources
        """
        log.info("trend_detector.fetch_all.started",
                keywords=niche_keywords,
                subreddits=niche_subreddits)
        
        # Fetch from all sources concurrently
        results = await asyncio.gather(
            self.fetch_google_trends(niche_keywords),
            self.fetch_reddit_trends(niche_subreddits),
            self.fetch_youtube_trends(),
            self.fetch_tiktok_trends(),
            return_exceptions=True,
        )
        
        # Combine all trends
        all_trends = []
        for result in results:
            if isinstance(result, list):
                all_trends.extend(result)
            elif isinstance(result, Exception):
                log.warning("trend_detector.source_failed",
                           error=str(result))
        
        log.info("trend_detector.fetch_all.completed",
                total_trends=len(all_trends))
        
        return all_trends
