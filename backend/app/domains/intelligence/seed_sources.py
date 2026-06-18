"""Niche source registry seeder — populates source_registry from niche source_config.

Reads the source_config JSONB field from each niche and creates
corresponding SourceRegistry entries. This bridges the niche seed data
(which defines *what* to scrape) with the intelligence pipeline
(which reads SourceRegistry to know *where* to fetch).

Run after niche seeding on startup.
"""
from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.control.models import Niche
from app.domains.intelligence.models import SourceRegistry, SourceType

logger = structlog.get_logger(__name__)


# Maps source_config keys to SourceType enum values
_SOURCE_TYPE_MAP = {
    "rss": SourceType.RSS,
    "subreddits": SourceType.SUBREDDIT,
    "youtube_channels": SourceType.YOUTUBE_CHANNEL,
    "twitter_lists": SourceType.TWITTER_LIST,
    "arxiv_categories": SourceType.ARXIV,
    "github_trending": SourceType.GITHUB_TRENDING,
    "product_hunt": SourceType.PRODUCT_HUNT,
    "web_scrape": SourceType.WEB_SCRAPE,
    "api": SourceType.API,
}

# Default fetch frequencies by source type (in minutes)
_FETCH_FREQUENCIES = {
    SourceType.RSS: 120,              # Every 2 hours
    SourceType.SUBREDDIT: 240,        # Every 4 hours
    SourceType.YOUTUBE_CHANNEL: 360,  # Every 6 hours
    SourceType.TWITTER_LIST: 240,     # Every 4 hours
    SourceType.ARXIV: 720,            # Every 12 hours
    SourceType.GITHUB_TRENDING: 480,  # Every 8 hours
    SourceType.PRODUCT_HUNT: 720,     # Every 12 hours
    SourceType.WEB_SCRAPE: 360,       # Every 6 hours
    SourceType.API: 240,              # Every 4 hours
}


def _build_entries_from_config(
    niche_id, niche_slug: str, source_config: dict,
) -> list[dict]:
    """Convert a niche's source_config JSON into SourceRegistry entry dicts."""
    entries = []

    # RSS feeds — list of URLs
    for url in source_config.get("rss", []):
        domain = url.split("//")[-1].split("/")[0] if "//" in url else url
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.RSS,
            "source_name": f"RSS: {domain} ({niche_slug})",
            "source_url": url,
            "feed_url": url,
            "reliability_score": 0.85,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.RSS],
        })

    # Subreddits — list of subreddit names
    for sub in source_config.get("subreddits", []):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.SUBREDDIT,
            "source_name": f"r/{sub} ({niche_slug})",
            "source_url": f"https://www.reddit.com/r/{sub}/",
            "feed_url": f"https://www.reddit.com/r/{sub}/hot.json",
            "reliability_score": 0.75,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.SUBREDDIT],
        })

    # YouTube channels — list of channel IDs or names
    for channel in source_config.get("youtube_channels", []):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.YOUTUBE_CHANNEL,
            "source_name": f"YouTube: {channel} ({niche_slug})",
            "source_url": f"https://www.youtube.com/channel/{channel}",
            "reliability_score": 0.80,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.YOUTUBE_CHANNEL],
        })

    # arXiv categories
    for category in source_config.get("arxiv_categories", []):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.ARXIV,
            "source_name": f"arXiv: {category} ({niche_slug})",
            "source_url": f"https://arxiv.org/list/{category}/recent",
            "feed_url": f"https://export.arxiv.org/rss/{category}",
            "reliability_score": 0.95,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.ARXIV],
        })

    # GitHub trending (boolean flag)
    if source_config.get("github_trending"):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.GITHUB_TRENDING,
            "source_name": f"GitHub Trending ({niche_slug})",
            "source_url": "https://github.com/trending",
            "reliability_score": 0.85,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.GITHUB_TRENDING],
        })

    # Product Hunt (boolean flag)
    if source_config.get("product_hunt"):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.PRODUCT_HUNT,
            "source_name": f"Product Hunt ({niche_slug})",
            "source_url": "https://www.producthunt.com/",
            "reliability_score": 0.80,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.PRODUCT_HUNT],
        })

    # Web scrape targets — list of URLs
    for url in source_config.get("web_scrape", []):
        domain = url.split("//")[-1].split("/")[0] if "//" in url else url
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.WEB_SCRAPE,
            "source_name": f"Scrape: {domain} ({niche_slug})",
            "source_url": url,
            "reliability_score": 0.70,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.WEB_SCRAPE],
        })

    # Twitter lists — list of list IDs or URLs
    for t_list in source_config.get("twitter_lists", []):
        entries.append({
            "niche_id": niche_id,
            "source_type": SourceType.TWITTER_LIST,
            "source_name": f"X List: {t_list} ({niche_slug})",
            "source_url": f"https://x.com/i/lists/{t_list}" if t_list.isdigit() else t_list,
            "reliability_score": 0.75,
            "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.TWITTER_LIST],
        })

    # API endpoints — list of dicts with name and url
    for api_source in source_config.get("api", []):
        if isinstance(api_source, dict):
            entries.append({
                "niche_id": niche_id,
                "source_type": SourceType.API,
                "source_name": api_source.get("name", f"API ({niche_slug})"),
                "source_url": api_source.get("url", ""),
                "scrape_config": api_source.get("config"),
                "reliability_score": 0.80,
                "fetch_frequency_minutes": _FETCH_FREQUENCIES[SourceType.API],
            })

    return entries


async def seed_niche_sources(db: AsyncSession) -> int:
    """Seed SourceRegistry from niche source_config fields.

    Skips niches that already have source entries.
    Returns count of new entries created.
    """
    # Get all niches with source_config
    result = await db.execute(select(Niche).where(Niche.is_active == True))
    niches = result.scalars().all()

    total_created = 0

    for niche in niches:
        source_config = getattr(niche, "source_config", None)
        if not source_config or not isinstance(source_config, dict):
            continue

        # Check if this niche already has sources
        existing = await db.execute(
            select(SourceRegistry.id).where(
                SourceRegistry.niche_id == niche.id
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        entries = _build_entries_from_config(niche.id, niche.slug, source_config)

        for entry_data in entries:
            source = SourceRegistry(**entry_data)
            db.add(source)
            total_created += 1

        logger.info(
            "niche_sources_seeded",
            niche=niche.slug,
            count=len(entries),
        )

    if total_created > 0:
        await db.commit()

    return total_created
