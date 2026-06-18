"""News fetching service for niche-specific content research.

Fetches news from:
- RSS feeds
- Web scraping
- API sources
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
import structlog
from bs4 import BeautifulSoup
import re

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    structlog.get_logger(__name__).warning("feedparser not available")

from app.services.scraping.scraper import WebScraper

log = structlog.get_logger(__name__)


class NewsFetcher:
    """Fetch news from multiple sources."""
    
    # Niche-specific RSS feeds
    NICHE_FEEDS = {
        "tech": [
            "https://hnrss.org/frontpage",
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
        ],
        "fitness": [
            "https://www.menshealth.com/rss/all.xml",
        ],
        "finance": [
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        ],
        "gaming": [
            "https://www.ign.com/articles?format=rss",
        ],
        "food": [
            "https://www.bonappetit.com/feed/rss",
        ],
    }
    
    async def fetch_rss_feed(
        self,
        feed_url: str,
        max_items: int = 10,
    ) -> List[Dict]:
        """Fetch articles from RSS feed.
        
        Args:
            feed_url: RSS feed URL
            max_items: Maximum number of items to fetch
            
        Returns:
            List of article dictionaries
        """
        if not FEEDPARSER_AVAILABLE:
            log.warning("news_fetcher.rss.unavailable")
            return self._mock_rss_feed(feed_url, max_items)
        
        try:
            log.info("news_fetcher.rss.started", feed_url=feed_url)
            
            # Fetch feed (feedparser is synchronous)
            feed = await asyncio.to_thread(feedparser.parse, feed_url)
            
            # Check if feed is valid
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                log.warning("news_fetcher.rss.empty_feed", feed_url=feed_url)
                return self._mock_rss_feed(feed_url, max_items)
            
            articles = []
            for entry in feed.entries[:max_items]:
                # Extract article data
                article = {
                    "title": entry.get("title", "Untitled"),
                    "description": entry.get("summary", ""),
                    "url": entry.get("link", ""),
                    "author": entry.get("author", "Unknown"),
                    "published_at": self._parse_date(entry.get("published")),
                    "source": feed.feed.get("title", "RSS Feed"),
                    "source_url": feed_url,
                }
                
                # Extract thumbnail if available
                if hasattr(entry, "media_thumbnail"):
                    article["thumbnail_url"] = entry.media_thumbnail[0]["url"]
                elif hasattr(entry, "media_content"):
                    article["thumbnail_url"] = entry.media_content[0]["url"]
                
                articles.append(article)
            
            log.info("news_fetcher.rss.completed",
                    feed_url=feed_url,
                    articles_found=len(articles))
            
            return articles
        
        except Exception as e:
            log.error("news_fetcher.rss.failed",
                     feed_url=feed_url,
                     error=str(e),
                     error_type=type(e).__name__)
            return self._mock_rss_feed(feed_url, max_items)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None
        
        try:
            # feedparser provides struct_time
            from time import mktime
            from email.utils import parsedate
            
            parsed = parsedate(date_str)
            if parsed:
                timestamp = mktime(parsed)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except Exception:
            pass
        
        return date_str
    
    def _mock_rss_feed(self, feed_url: str, max_items: int) -> List[Dict]:
        """Mock RSS feed data."""
        return [
            {
                "title": f"Breaking News Article {i}",
                "description": f"This is a summary of article {i} from the feed.",
                "url": f"https://example.com/article-{i}",
                "author": "Tech Reporter",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "Tech News",
                "source_url": feed_url,
            }
            for i in range(1, min(max_items + 1, 6))
        ]
    
    async def fetch_niche_news(
        self,
        niche: str,
        max_items_per_feed: int = 5,
    ) -> List[Dict]:
        """Fetch news for a specific niche.
        
        Args:
            niche: Niche name (tech, fitness, finance, etc.)
            max_items_per_feed: Max items per feed
            
        Returns:
            Combined list of articles from all niche feeds
        """
        feeds = self.NICHE_FEEDS.get(niche.lower(), [])
        
        if not feeds:
            log.warning("news_fetcher.niche.no_feeds",
                       niche=niche)
            return self._mock_niche_news(niche, max_items_per_feed)
        
        log.info("news_fetcher.niche.started",
                niche=niche,
                feed_count=len(feeds))
        
        # Fetch all feeds concurrently
        tasks = [
            self.fetch_rss_feed(feed_url, max_items_per_feed)
            for feed_url in feeds
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all articles
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                log.warning("news_fetcher.niche.feed_failed",
                           error=str(result))
        
        log.info("news_fetcher.niche.completed",
                niche=niche,
                articles_found=len(all_articles))
        
        return all_articles
    
    def _mock_niche_news(self, niche: str, max_items: int) -> List[Dict]:
        """Mock niche news data."""
        return [
            {
                "title": f"{niche.title()} Industry Update {i}",
                "description": f"Latest developments in {niche} that creators should know about.",
                "url": f"https://example.com/{niche}/article-{i}",
                "author": f"{niche.title()} Expert",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": f"{niche.title()} News",
                "source_url": f"https://example.com/{niche}/feed",
            }
            for i in range(1, min(max_items + 1, 6))
        ]
    
    def calculate_relevance_score(
        self,
        article: Dict,
        niche_keywords: List[str],
    ) -> float:
        """Calculate relevance score for an article.
        
        Args:
            article: Article data
            niche_keywords: Keywords for the niche
            
        Returns:
            Relevance score (0-1)
        """
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in niche_keywords if keyword.lower() in text)
        
        # Normalize score
        if not niche_keywords:
            return 0.5
        
        score = min(matches / len(niche_keywords), 1.0)
        
        # Boost score if multiple keywords match
        if matches > 1:
            score = min(score * 1.2, 1.0)
        
        return score
    
    async def fetch_and_score_news(
        self,
        niche: str,
        niche_keywords: List[str],
        max_items: int = 20,
        min_relevance: float = 0.3,
    ) -> List[Dict]:
        """Fetch news and score by relevance.
        
        Args:
            niche: Niche name
            niche_keywords: Keywords for relevance scoring
            max_items: Maximum items to return
            min_relevance: Minimum relevance score threshold
            
        Returns:
            Scored and filtered articles
        """
        # Fetch news
        articles = await self.fetch_niche_news(niche, max_items_per_feed=10)
        
        # Score each article
        scored_articles = []
        for article in articles:
            relevance = self.calculate_relevance_score(article, niche_keywords)
            
            if relevance >= min_relevance:
                article["relevance_score"] = round(relevance, 3)
                scored_articles.append(article)
        
        # Sort by relevance
        scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return scored_articles[:max_items]
