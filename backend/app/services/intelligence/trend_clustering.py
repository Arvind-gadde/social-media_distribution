"""Trend clustering - Group similar trends together."""
import structlog
from typing import List, Dict, Any
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.domains.intelligence.models import Trend

log = structlog.get_logger(__name__)

def calculate_similarity(trend1: str, trend2: str) -> float:
    """Calculate similarity between two trend titles using simple word overlap."""
    words1 = set(trend1.lower().split())
    words2 = set(trend2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

async def cluster_trends(db: AsyncSession, niche_id: str, similarity_threshold: float = 0.3) -> Dict[str, List[str]]:
    """Cluster similar trends together.
    
    Args:
        db: Database session
        niche_id: Niche UUID
        similarity_threshold: Minimum similarity to group trends (0-1)
    
    Returns:
        Dictionary mapping cluster representative to list of trend IDs
    """
    # Get recent trends for niche
    result = await db.execute(
        select(Trend).where(
            Trend.niche_id == niche_id,
            Trend.status.in_(["rising", "peak"])
        ).order_by(Trend.trend_score.desc())
    )
    trends = result.scalars().all()
    
    if not trends:
        return {}
    
    # Build clusters
    clusters = defaultdict(list)
    processed = set()
    
    for i, trend1 in enumerate(trends):
        if str(trend1.id) in processed:
            continue
        
        # Start new cluster with this trend as representative
        cluster_key = trend1.title
        clusters[cluster_key].append(str(trend1.id))
        processed.add(str(trend1.id))
        
        # Find similar trends
        for j, trend2 in enumerate(trends[i+1:], start=i+1):
            if str(trend2.id) in processed:
                continue
            
            similarity = calculate_similarity(trend1.title, trend2.title)
            if similarity >= similarity_threshold:
                clusters[cluster_key].append(str(trend2.id))
                processed.add(str(trend2.id))
    
    log.info("trends_clustered", 
             niche_id=niche_id,
             total_trends=len(trends),
             clusters=len(clusters))
    
    return dict(clusters)

async def get_cluster_summary(db: AsyncSession, trend_ids: List[str]) -> Dict[str, Any]:
    """Get summary statistics for a trend cluster.
    
    Args:
        db: Database session
        trend_ids: List of trend IDs in cluster
    
    Returns:
        Cluster summary with aggregated metrics
    """
    result = await db.execute(
        select(Trend).where(Trend.id.in_(trend_ids))
    )
    trends = result.scalars().all()
    
    if not trends:
        return {}
    
    # Aggregate metrics
    total_score = sum(t.trend_score or 0 for t in trends)
    avg_score = total_score / len(trends)
    max_score = max(t.trend_score or 0 for t in trends)
    
    # Collect all platforms
    platforms = set()
    for t in trends:
        if t.platform:
            platforms.add(t.platform)
    
    # Collect all hashtags
    all_hashtags = []
    for t in trends:
        if t.hashtags:
            all_hashtags.extend(t.hashtags)
    
    # Count hashtag frequency
    hashtag_counts = defaultdict(int)
    for tag in all_hashtags:
        hashtag_counts[tag] += 1
    
    top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "trend_count": len(trends),
        "avg_score": round(avg_score, 2),
        "max_score": round(max_score, 2),
        "platforms": list(platforms),
        "top_hashtags": [tag for tag, _ in top_hashtags],
        "representative_title": trends[0].title if trends else "",
    }
