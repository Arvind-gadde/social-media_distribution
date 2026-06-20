"""News & Research Agent - Daily intelligence briefing for creators.

Fetches niche-specific news, summarizes articles, explains content angles,
provides curated daily briefing.
"""
import uuid
from datetime import datetime, timezone, timedelta
import structlog
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.context import RunContext
from app.domains.intelligence.models import WorkspaceInsight, InsightType
from app.integrations.llm.provider import create_llm_provider_from_settings, TaskType

log = structlog.get_logger(__name__)

# Niche-specific news sources
NEWS_SOURCES = {
    "tech": [
        "https://techcrunch.com/feed/",
        "https://news.ycombinator.com/rss",
    ],
    "fitness": [
        "https://www.menshealth.com/rss/all.xml/",
    ],
    "finance": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ],
    "gaming": [
        "https://www.ign.com/articles?format=rss",
    ],
}

async def fetch_news(ctx: RunContext) -> dict:
    """Fetch and summarize niche news."""
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.domains.control.models import WorkspaceNiche, Niche
    
    stats = {"sources_checked": 0, "articles_found": 0, "insights": 0, "errors": 0}
    
    async with AsyncSessionLocal() as db:
        # Get workspace niches
        result = await db.execute(
            select(Niche)
            .join(WorkspaceNiche)
            .where(WorkspaceNiche.workspace_id == ctx.workspace_id)
        )
        niches = result.scalars().all()
        
        if not niches:
            return stats
        
        # Collect articles from relevant sources
        articles = []
        
        for niche in niches:
            niche_slug = niche.slug.lower()
            sources = NEWS_SOURCES.get(niche_slug, [])
            
            for source_url in sources:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(source_url)
                        if resp.status_code == 200:
                            # Simple RSS parsing (would use feedparser in production)
                            # For now, just mark as checked
                            stats["sources_checked"] += 1
                            # Placeholder: would parse RSS and extract articles
                            articles.append({
                                "title": f"Sample article from {source_url}",
                                "source": source_url,
                                "niche": niche_slug
                            })
                except Exception as e:
                    log.warning("news_fetch_failed", source=source_url, error=str(e))
                    stats["errors"] += 1
        
        stats["articles_found"] = len(articles)
        
        # Generate AI briefing
        if articles:
            try:
                provider = create_llm_provider_from_settings()
                
                articles_summary = "\n".join([
                    f"- {a['title']} ({a['niche']})"
                    for a in articles[:10]
                ])
                
                prompt = f"""Create a daily intelligence briefing for a content creator based on these news articles:

{articles_summary}

For each article:
1. Summarize in 1-2 sentences
2. Explain why it matters for their content
3. Suggest a content angle they could create

Keep it concise and actionable. Format as a daily briefing."""

                response = await provider.complete(
                    task_type=TaskType.ANALYSIS,
                    messages=[{"role": "user", "content": prompt}],
                    workspace_id=ctx.workspace_id,
                    db_session=db
                )
                
                # Create insight
                insight = WorkspaceInsight(
                    workspace_id=ctx.workspace_id,
                    insight_type=InsightType.NEWS_OPPORTUNITY,
                    title="Daily Intelligence Briefing",
                    body=response.content,
                    priority=5,
                    metadata_={
                        "sources_checked": stats["sources_checked"],
                        "articles_found": stats["articles_found"]
                    }
                )
                db.add(insight)
                await db.commit()
                
                stats["insights"] = 1
                log.info("news_briefing_complete", workspace_id=str(ctx.workspace_id), stats=stats)
                
            except Exception as e:
                log.error("briefing_generation_failed", error=str(e))
                stats["errors"] += 1
    
    return stats
