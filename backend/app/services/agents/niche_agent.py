"""Niche Intelligence Agent - Learns and adapts to creator's content niche.

Analyzes past performance, identifies best content pillars, suggests niche
expansion/refinement, builds audience interest graph.
"""
import uuid
from datetime import datetime, timezone, timedelta
import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.context import RunContext
from app.domains.intelligence.models import WorkspaceInsight, InsightType
from app.domains.execution.models import ContentVariant
from app.services.llm.provider import create_llm_provider, TaskType
from app.services.niche.content_index import find_similar, index_variants

log = structlog.get_logger(__name__)

async def analyze_niche(ctx: RunContext) -> dict:
    """Analyze workspace niche performance and generate recommendations."""
    from app.db.session import AsyncSessionLocal
    
    stats = {"analyzed": 0, "insights": 0, "errors": 0}
    
    async with AsyncSessionLocal() as db:
        # Get recent content performance (last 90 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await db.execute(
            select(ContentVariant)
            .where(
                ContentVariant.workspace_id == ctx.workspace_id,
                ContentVariant.created_at >= cutoff,
                ContentVariant.status == "published"
            )
            .order_by(desc(ContentVariant.created_at))
            .limit(100)
        )
        variants = result.scalars().all()
        
        if not variants:
            log.info("no_content_for_analysis", workspace_id=str(ctx.workspace_id))
            return stats
        
        stats["analyzed"] = len(variants)

        # Index variants into Qdrant so we can do semantic clustering. No-op
        # when Qdrant or OpenAI keys are missing — the agent still returns the
        # pillar-based analysis below.
        try:
            indexed = await index_variants(ctx.workspace_id, variants)
            stats["indexed"] = indexed
        except Exception as exc:
            log.warning("niche_index_failed", error=str(exc))
            stats["indexed"] = 0

        # Cluster signal: pull a handful of semantically-related posts for each
        # top variant's caption so we can show the LLM real evidence of which
        # topics resonate beyond the explicit pillar tags.
        related_samples: list[dict] = []
        for sample in variants[:5]:
            text = (sample.title or "") + " " + (sample.caption or "")
            if not text.strip():
                continue
            try:
                hits = await find_similar(
                    ctx.workspace_id, text, limit=5, score_threshold=0.7
                )
            except Exception as exc:
                log.warning("niche_similarity_failed", error=str(exc))
                continue
            if hits:
                related_samples.append({
                    "seed_title": sample.title or "(untitled)",
                    "neighbors": [
                        {"id": h.id, "score": round(h.score, 3), "platform": h.payload.get("platform")}
                        for h in hits
                    ],
                })

        # Analyze performance by content pillar
        pillar_performance = {}
        for variant in variants:
            pillars = variant.content_pillars or []
            engagement = variant.engagement_rate or 0
            
            for pillar in pillars:
                if pillar not in pillar_performance:
                    pillar_performance[pillar] = {"count": 0, "total_engagement": 0}
                pillar_performance[pillar]["count"] += 1
                pillar_performance[pillar]["total_engagement"] += engagement
        
        # Calculate averages
        pillar_analysis = []
        for pillar, data in pillar_performance.items():
            avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0
            pillar_analysis.append({
                "pillar": pillar,
                "count": data["count"],
                "avg_engagement": avg_engagement
            })
        
        # Sort by engagement
        pillar_analysis.sort(key=lambda x: x["avg_engagement"], reverse=True)
        
        # Generate AI insights
        try:
            provider = await create_llm_provider(
                task_type=TaskType.ANALYSIS,
                workspace_id=ctx.workspace_id,
                db_session=db
            )
            
            prompt = f"""Analyze this creator's content performance data:

Top performing content pillars:
{pillar_analysis[:5]}

Semantic neighborhood clusters (each row = one seed post + its nearest
neighbors in our vector index; high cosine score = topic overlap):
{related_samples or "no embedding index available yet"}

Total content pieces: {len(variants)}
Analysis period: Last 90 days

Provide:
1. Which content pillars are working best (top 3)
2. Suggested niche refinement or expansion
3. Content gaps to fill
4. Audience interest patterns
5. Any audience-interest clusters visible from the semantic neighborhoods

Be specific and actionable."""

            response = await provider.complete(
                task_type=TaskType.ANALYSIS,
                messages=[{"role": "user", "content": prompt}],
                workspace_id=ctx.workspace_id,
                db_session=db
            )
            
            # Create insight
            insight = WorkspaceInsight(
                workspace_id=ctx.workspace_id,
                insight_type=InsightType.NICHE_ANALYSIS,
                title="Niche Performance Analysis",
                body=response.text,
                priority=7,
                metadata_={
                    "pillar_analysis": pillar_analysis[:5],
                    "total_analyzed": len(variants),
                    "indexed_in_qdrant": stats.get("indexed", 0),
                    "semantic_clusters": related_samples,
                }
            )
            db.add(insight)
            await db.commit()
            
            stats["insights"] = 1
            log.info("niche_analysis_complete", workspace_id=str(ctx.workspace_id), stats=stats)
            
        except Exception as e:
            log.error("niche_analysis_failed", error=str(e))
            stats["errors"] += 1
    
    return stats
