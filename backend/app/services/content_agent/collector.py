"""
Collector — fetches content from all free sources and stores in DB.
Runs via Celery beat every 2 hours.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import structlog

from app.services.content_agent.sources import (
    Source, NITTER_INSTANCES, get_all_sources
)

logger = structlog.get_logger(__name__)

HEADERS = {
    "User-Agent": "ContentFlow-Agent/1.0 (content aggregator)",
    "Accept": "application/json, application/xml, text/html, */*",
}

MAX_AGE_HOURS = 48


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, AttributeError):
            continue
    return None


def _is_too_old(published_at: Optional[datetime]) -> bool:
    if not published_at:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    return published_at < cutoff


def _clean_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class RawItem:
    def __init__(self, source, title, url, content="", author="", published_at=None):
        self.source = source
        self.title = title.strip()[:1000]
        self.url = url.strip()
        self.content = content[:8000]
        self.author = author[:200]
        self.published_at = published_at


async def _fetch_rss(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    try:
        import feedparser
        resp = await client.get(source.url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        items = []
        for entry in feed.entries[:15]:
            url = getattr(entry, "link", None) or getattr(entry, "id", None)
            if not url:
                continue
            title = getattr(entry, "title", "")
            content = ""
            if hasattr(entry, "content"):
                content = _clean_html(entry.content[0].get("value", ""))
            elif hasattr(entry, "summary"):
                content = _clean_html(entry.summary)
            published_at = _parse_dt(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            )
            if _is_too_old(published_at):
                continue
            items.append(RawItem(
                source=source, title=title, url=url, content=content,
                author=getattr(getattr(entry, "author_detail", None), "name", ""),
                published_at=published_at,
            ))
        return items
    except Exception as exc:
        logger.warning("rss_fetch_failed", source=source.key, error=str(exc))
        return []


async def _fetch_nitter(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    username = source.url.split("/")[-2]
    for instance in NITTER_INSTANCES:
        try:
            import feedparser
            url = f"https://{instance}/{username}/rss"
            resp = await client.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            if not feed.entries:
                continue
            items = []
            for entry in feed.entries[:10]:
                tweet_url = getattr(entry, "link", "")
                title = _clean_html(getattr(entry, "title", ""))
                content = _clean_html(getattr(entry, "summary", ""))
                published_at = _parse_dt(getattr(entry, "published", None))
                if _is_too_old(published_at) or not title or len(title) < 15:
                    continue
                items.append(RawItem(
                    source=source, title=title[:280], url=tweet_url,
                    content=content, published_at=published_at,
                ))
            return items
        except Exception:
            continue
    logger.warning("nitter_all_failed", source=source.key)
    return []


async def _fetch_youtube(source: Source, client: httpx.AsyncClient, api_key: str) -> list[RawItem]:
    channel_id = source.url
    if not api_key:
        return []
    try:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": api_key, "channelId": channel_id, "part": "snippet",
                "order": "date", "maxResults": 5, "type": "video",
                "publishedAfter": (datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, timeout=15
        )
        resp.raise_for_status()
        items = []
        for item in resp.json().get("items", []):
            snippet = item.get("snippet", {})
            vid_id = item.get("id", {}).get("videoId", "")
            if not vid_id:
                continue
            items.append(RawItem(
                source=source, title=snippet.get("title", ""),
                url=f"https://www.youtube.com/watch?v={vid_id}",
                content=snippet.get("description", ""),
                author=snippet.get("channelTitle", ""),
                published_at=_parse_dt(snippet.get("publishedAt")),
            ))
        return items
    except Exception as exc:
        logger.warning("youtube_fetch_failed", source=source.key, error=str(exc))
        return []


async def _fetch_github(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    repo = source.url
    try:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}/releases",
            headers={**HEADERS, "Accept": "application/vnd.github+json"}, timeout=15,
        )
        resp.raise_for_status()
        items = []
        for release in resp.json()[:5]:
            if release.get("draft") or release.get("prerelease"):
                continue
            published_at = _parse_dt(release.get("published_at"))
            if _is_too_old(published_at):
                continue
            items.append(RawItem(
                source=source,
                title=f"{repo.split('/')[1]} {release.get('tag_name', '')} released",
                url=release.get("html_url", ""),
                content=_clean_html((release.get("body") or "")[:3000]),
                author=release.get("author", {}).get("login", ""),
                published_at=published_at,
            ))
        return items
    except Exception as exc:
        logger.warning("github_fetch_failed", source=source.key, error=str(exc))
        return []


async def _fetch_reddit(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    subreddit = source.url
    try:
        resp = await client.get(
            f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15",
            headers={**HEADERS, "User-Agent": "ContentFlow-Agent:1.0"}, timeout=15,
        )
        resp.raise_for_status()
        items = []
        for post in resp.json().get("data", {}).get("children", []):
            d = post.get("data", {})
            if d.get("stickied") or d.get("score", 0) < 50:
                continue
            published_at = datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc)
            if _is_too_old(published_at):
                continue
            items.append(RawItem(
                source=source, title=d.get("title", ""),
                url=f"https://reddit.com{d.get('permalink', '')}",
                content=(d.get("selftext", "") or d.get("url", ""))[:3000],
                author=d.get("author", ""), published_at=published_at,
            ))
        return items
    except Exception as exc:
        logger.warning("reddit_fetch_failed", source=source.key, error=str(exc))
        return []


async def _fetch_hackernews(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    try:
        resp = await client.get(source.url, timeout=15)
        resp.raise_for_status()
        items = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
        for hit in resp.json().get("hits", []):
            if hit.get("points", 0) < 30:
                continue
            created = datetime.fromtimestamp(hit.get("created_at_i", 0), tz=timezone.utc)
            if created < cutoff:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            items.append(RawItem(
                source=source, title=hit.get("title", ""), url=url,
                content=hit.get("story_text") or "",
                author=hit.get("author", ""), published_at=created,
            ))
        return items
    except Exception as exc:
        logger.warning("hn_fetch_failed", source=source.key, error=str(exc))
        return []


async def _fetch_linkedin(source: Source, client: httpx.AsyncClient) -> list[RawItem]:
    try:
        resp = await client.get(
            source.url,
            headers={**HEADERS, "Accept-Language": "en-US,en;q=0.9"},
            timeout=20, follow_redirects=True,
        )
        if resp.status_code in (429, 999):
            return []
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        articles = (
            soup.find_all("article", limit=5) or
            soup.find_all(class_=re.compile(r"(base-card|feed-shared-update)", re.I), limit=5)
        )
        for article in articles:
            text_el = article.find(class_=re.compile(r"(feed-shared-text|commentary)", re.I))
            if not text_el:
                text_el = article.find("p")
            if not text_el:
                continue
            text = text_el.get_text(separator=" ").strip()
            if len(text) < 40:
                continue
            link_el = article.find("a", href=re.compile(r"/posts/|/feed/update/"))
            url = source.url
            if link_el:
                href = link_el.get("href", "")
                url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
            items.append(RawItem(
                source=source, title=text[:200], url=url,
                content=text, published_at=datetime.now(timezone.utc),
            ))
        return items
    except Exception as exc:
        logger.warning("linkedin_fetch_failed", source=source.key, error=str(exc))
        return []


async def collect_all(youtube_api_key: str = "") -> dict:
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.models.models import ContentItem
    from sqlalchemy import select

    sources = get_all_sources()
    all_items: list[RawItem] = []

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        tasks = []
        for src in sources:
            if src.type == "rss":
                tasks.append(_fetch_rss(src, client))
            elif src.type == "nitter":
                tasks.append(_fetch_nitter(src, client))
            elif src.type == "youtube":
                tasks.append(_fetch_youtube(src, client, youtube_api_key))
            elif src.type == "github":
                tasks.append(_fetch_github(src, client))
            elif src.type == "reddit":
                tasks.append(_fetch_reddit(src, client))
            elif src.type == "hackernews":
                tasks.append(_fetch_hackernews(src, client))
            elif src.type == "linkedin_scrape":
                tasks.append(_fetch_linkedin(src, client))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_items.extend(result)

    logger.info("collection_raw_items", count=len(all_items))

    new_count = 0
    async with AsyncSessionLocal() as db:
        for item in all_items:
            if not item.url or not item.title:
                continue
            exists = await db.execute(
                select(ContentItem.id).where(ContentItem.source_url == item.url).limit(1)
            )
            if exists.scalar_one_or_none():
                continue
            db.add(ContentItem(
                source_key=item.source.key,
                source_label=item.source.label,
                source_url=item.url,
                title=item.title,
                raw_content=item.content,
                author=item.author,
                published_at=item.published_at,
                is_processed=False,
            ))
            new_count += 1
        await db.commit()

    logger.info("collection_complete", new_items=new_count, total_fetched=len(all_items))
    return {"fetched": len(all_items), "new": new_count}
