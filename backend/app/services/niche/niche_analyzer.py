"""Niche analysis service for understanding creator's content focus.

Analyzes:
- Content performance by topic
- Best performing content pillars
- Niche expansion opportunities
- Audience interest patterns
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from collections import Counter
import structlog

log = structlog.get_logger(__name__)


class NicheAnalyzer:
    """Analyze creator's niche and content performance patterns."""
    
    def analyze_content_performance(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Analyze content performance by topic/pillar.
        
        Args:
            content_items: List of content items with metadata
            
        Returns:
            Analysis results with top performing topics
        """
        if not content_items:
            return {
                "total_content": 0,
                "top_topics": [],
                "performance_by_topic": {},
                "recommendations": [],
            }
        
        # Extract topics from content
        topic_performance = {}
        
        for item in content_items:
            # Get topics/tags from content
            topics = item.get("topics", []) or item.get("tags", []) or []
            
            # If no topics, try to extract from title
            if not topics and item.get("title"):
                # Simple keyword extraction (in production, use NLP)
                title_words = item.get("title", "").lower().split()
                topics = [word for word in title_words if len(word) > 4][:3]
            
            # Track performance per topic
            for topic in topics:
                if topic not in topic_performance:
                    topic_performance[topic] = {
                        "count": 0,
                        "total_views": 0,
                        "total_engagement": 0,
                        "avg_engagement_rate": 0.0,
                    }
                
                topic_performance[topic]["count"] += 1
                topic_performance[topic]["total_views"] += item.get("views", 0)
                
                # Calculate engagement (likes + comments + shares)
                engagement = (
                    item.get("likes", 0) +
                    item.get("comments", 0) +
                    item.get("shares", 0)
                )
                topic_performance[topic]["total_engagement"] += engagement
        
        # Calculate averages
        for topic, stats in topic_performance.items():
            if stats["count"] > 0:
                stats["avg_views"] = stats["total_views"] / stats["count"]
                stats["avg_engagement"] = stats["total_engagement"] / stats["count"]
                
                # Engagement rate = engagement / views (if views > 0)
                if stats["total_views"] > 0:
                    stats["avg_engagement_rate"] = (
                        stats["total_engagement"] / stats["total_views"]
                    )
        
        # Sort topics by performance
        sorted_topics = sorted(
            topic_performance.items(),
            key=lambda x: (x[1]["avg_engagement_rate"], x[1]["count"]),
            reverse=True,
        )
        
        # Get top 10 topics
        top_topics = [
            {
                "topic": topic,
                "count": stats["count"],
                "avg_views": round(stats.get("avg_views", 0), 2),
                "avg_engagement": round(stats.get("avg_engagement", 0), 2),
                "avg_engagement_rate": round(stats["avg_engagement_rate"], 4),
            }
            for topic, stats in sorted_topics[:10]
        ]
        
        return {
            "total_content": len(content_items),
            "unique_topics": len(topic_performance),
            "top_topics": top_topics,
            "performance_by_topic": dict(sorted_topics),
        }
    
    def identify_content_pillars(
        self,
        content_items: List[Dict],
        min_content_count: int = 3,
    ) -> List[Dict]:
        """Identify main content pillars based on frequency and performance.
        
        Args:
            content_items: List of content items
            min_content_count: Minimum number of posts to be considered a pillar
            
        Returns:
            List of content pillars with performance metrics
        """
        if not content_items:
            return []
        
        # Analyze performance
        analysis = self.analyze_content_performance(content_items)
        
        # Filter topics that appear frequently enough
        pillars = [
            topic for topic in analysis["top_topics"]
            if topic["count"] >= min_content_count
        ]
        
        # Add pillar strength score (0-1)
        for pillar in pillars:
            # Score based on frequency and engagement
            frequency_score = min(pillar["count"] / len(content_items), 1.0)
            engagement_score = min(pillar["avg_engagement_rate"] * 10, 1.0)
            
            pillar["strength_score"] = round(
                (frequency_score * 0.4) + (engagement_score * 0.6),
                3,
            )
        
        # Sort by strength
        pillars.sort(key=lambda x: x["strength_score"], reverse=True)
        
        return pillars
    
    def suggest_niche_expansion(
        self,
        current_pillars: List[Dict],
        related_topics: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Suggest niche expansion opportunities.
        
        Args:
            current_pillars: Current content pillars
            related_topics: Optional list of related topics to consider
            
        Returns:
            List of expansion suggestions
        """
        suggestions = []
        
        if not current_pillars:
            return [{
                "suggestion": "Start creating consistent content to establish pillars",
                "rationale": "No clear content pillars identified yet",
                "priority": "high",
            }]
        
        # Analyze pillar diversity
        pillar_count = len(current_pillars)
        
        if pillar_count < 3:
            suggestions.append({
                "suggestion": "Expand to 3-5 core content pillars",
                "rationale": f"Currently only {pillar_count} pillar(s). Diversifying helps reach wider audience.",
                "priority": "high",
                "action": "Identify 2-3 related topics to your niche",
            })
        
        # Check for underperforming pillars
        if pillar_count > 0:
            avg_strength = sum(p["strength_score"] for p in current_pillars) / pillar_count
            
            weak_pillars = [
                p for p in current_pillars
                if p["strength_score"] < avg_strength * 0.7
            ]
            
            if weak_pillars:
                suggestions.append({
                    "suggestion": f"Refine or replace weak pillar: {weak_pillars[0]['topic']}",
                    "rationale": f"Low engagement rate ({weak_pillars[0]['avg_engagement_rate']:.2%})",
                    "priority": "medium",
                    "action": "Try different angles or formats for this topic",
                })
        
        # Suggest doubling down on top performer
        if current_pillars:
            top_pillar = current_pillars[0]
            suggestions.append({
                "suggestion": f"Double down on '{top_pillar['topic']}'",
                "rationale": f"Highest engagement rate ({top_pillar['avg_engagement_rate']:.2%})",
                "priority": "high",
                "action": f"Create more content around {top_pillar['topic']}",
            })
        
        # Add related topic suggestions if provided
        if related_topics:
            for topic in related_topics[:3]:
                suggestions.append({
                    "suggestion": f"Explore '{topic}' as new pillar",
                    "rationale": "Related to your niche, potential for growth",
                    "priority": "low",
                    "action": f"Test 2-3 posts about {topic}",
                })
        
        return suggestions
    
    def build_audience_interest_graph(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Build audience interest graph from content performance.
        
        Args:
            content_items: List of content items with engagement data
            
        Returns:
            Interest graph with topics and connections
        """
        if not content_items:
            return {
                "interests": [],
                "connections": [],
                "top_interests": [],
            }
        
        # Extract topics and their co-occurrence
        topic_pairs = []
        all_topics = []
        
        for item in content_items:
            topics = item.get("topics", []) or item.get("tags", []) or []
            
            if not topics and item.get("title"):
                title_words = item.get("title", "").lower().split()
                topics = [word for word in title_words if len(word) > 4][:3]
            
            all_topics.extend(topics)
            
            # Track topic pairs (co-occurrence)
            for i, topic1 in enumerate(topics):
                for topic2 in topics[i+1:]:
                    topic_pairs.append((topic1, topic2))
        
        # Count topic frequency
        topic_counts = Counter(all_topics)
        
        # Count pair frequency
        pair_counts = Counter(topic_pairs)
        
        # Build interest nodes
        interests = [
            {
                "topic": topic,
                "frequency": count,
                "weight": round(count / len(content_items), 3),
            }
            for topic, count in topic_counts.most_common(20)
        ]
        
        # Build connections
        connections = [
            {
                "from": pair[0],
                "to": pair[1],
                "strength": count,
            }
            for pair, count in pair_counts.most_common(15)
        ]
        
        return {
            "interests": interests,
            "connections": connections,
            "top_interests": interests[:5],
            "total_topics": len(topic_counts),
        }
    
    def calculate_niche_focus_score(
        self,
        content_items: List[Dict],
    ) -> float:
        """Calculate how focused the creator is on their niche (0-1).
        
        Args:
            content_items: List of content items
            
        Returns:
            Focus score (0 = very diverse, 1 = very focused)
        """
        if not content_items or len(content_items) < 3:
            return 0.5  # Neutral score for insufficient data
        
        # Analyze topic distribution
        analysis = self.analyze_content_performance(content_items)
        
        if analysis["unique_topics"] == 0:
            return 0.5
        
        # Calculate concentration (how much content is in top topics)
        top_3_count = sum(
            topic["count"]
            for topic in analysis["top_topics"][:3]
        )
        
        concentration = top_3_count / len(content_items)
        
        # Calculate diversity penalty
        diversity_ratio = analysis["unique_topics"] / len(content_items)
        
        # Focus score: high concentration + low diversity = high focus
        focus_score = (concentration * 0.7) + ((1 - diversity_ratio) * 0.3)
        
        return round(min(focus_score, 1.0), 3)
