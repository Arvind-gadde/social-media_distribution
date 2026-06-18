"""Competitor analysis service for scoring content and identifying opportunities.

Analyzes competitor content to:
- Score virality (0-100)
- Extract topics and themes
- Identify content gaps
- Track performance trends
- Generate actionable insights
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import structlog

log = structlog.get_logger(__name__)


class CompetitorAnalyzer:
    """Analyze competitor content and identify opportunities."""
    
    def calculate_virality_score(
        self,
        content: Dict,
        platform: str,
    ) -> float:
        """Calculate virality score (0-100) for a piece of content.
        
        Args:
            content: Content data with engagement metrics
            platform: Platform name
            
        Returns:
            Virality score from 0-100
        """
        # Platform-specific scoring weights
        weights = {
            "instagram": {
                "likes": 0.3,
                "comments": 0.4,
                "saves": 0.2,
                "shares": 0.1,
            },
            "youtube": {
                "views": 0.4,
                "likes": 0.3,
                "comments": 0.2,
                "watch_time": 0.1,
            },
            "tiktok": {
                "views": 0.3,
                "likes": 0.25,
                "comments": 0.2,
                "shares": 0.25,
            },
        }
        
        platform_weights = weights.get(platform, weights["instagram"])
        
        # Normalize metrics (assuming typical ranges)
        normalized = {}
        
        if platform == "instagram":
            normalized["likes"] = min(content.get("likes", 0) / 10000, 1.0)
            normalized["comments"] = min(content.get("comments", 0) / 500, 1.0)
            normalized["saves"] = min(content.get("saves", 0) / 1000, 1.0)
            normalized["shares"] = min(content.get("shares", 0) / 500, 1.0)
        
        elif platform == "youtube":
            normalized["views"] = min(content.get("views", 0) / 100000, 1.0)
            normalized["likes"] = min(content.get("likes", 0) / 5000, 1.0)
            normalized["comments"] = min(content.get("comments", 0) / 500, 1.0)
            normalized["watch_time"] = 0.7  # Placeholder
        
        elif platform == "tiktok":
            normalized["views"] = min(content.get("views", 0) / 500000, 1.0)
            normalized["likes"] = min(content.get("likes", 0) / 50000, 1.0)
            normalized["comments"] = min(content.get("comments", 0) / 1000, 1.0)
            normalized["shares"] = min(content.get("shares", 0) / 2000, 1.0)
        
        # Calculate weighted score
        score = 0.0
        for metric, weight in platform_weights.items():
            score += normalized.get(metric, 0) * weight * 100
        
        return min(score, 100.0)
    
    def calculate_engagement_rate(
        self,
        content: Dict,
        followers: int,
        platform: str,
    ) -> float:
        """Calculate engagement rate for content.
        
        Args:
            content: Content data
            followers: Follower count
            platform: Platform name
            
        Returns:
            Engagement rate (0-1)
        """
        if followers == 0:
            return 0.0
        
        if platform == "instagram":
            engagements = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("saves", 0) * 2  # Saves count double
            )
        elif platform == "youtube":
            engagements = (
                content.get("likes", 0) +
                content.get("comments", 0) * 2
            )
        elif platform == "tiktok":
            engagements = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("shares", 0) * 3  # Shares count triple
            )
        else:
            engagements = content.get("likes", 0) + content.get("comments", 0)
        
        return min(engagements / followers, 1.0)
    
    def extract_topics(
        self,
        content: Dict,
        platform: str,
    ) -> List[str]:
        """Extract topics from content.
        
        Args:
            content: Content data
            platform: Platform name
            
        Returns:
            List of extracted topics
        """
        topics = []
        
        # Extract from hashtags
        hashtags = content.get("hashtags", [])
        for tag in hashtags:
            # Remove # and convert to topic
            topic = tag.replace("#", "").lower()
            if len(topic) > 3:  # Skip very short hashtags
                topics.append(topic)
        
        # Extract from caption/title/description
        text_fields = [
            content.get("caption", ""),
            content.get("title", ""),
            content.get("description", ""),
        ]
        
        # Simple keyword extraction (in production, use NLP)
        keywords = [
            "tutorial", "tips", "hack", "guide", "review",
            "how to", "best", "top", "secret", "viral",
            "productivity", "content", "creator", "ai",
        ]
        
        for text in text_fields:
            text_lower = text.lower()
            for keyword in keywords:
                if keyword in text_lower and keyword not in topics:
                    topics.append(keyword)
        
        return topics[:10]  # Limit to top 10
    
    def identify_content_gaps(
        self,
        competitor_content: List[Dict],
        user_content: List[Dict],
    ) -> List[Dict]:
        """Identify content gaps (what competitors do that user doesn't).
        
        Args:
            competitor_content: List of competitor content items
            user_content: List of user's content items
            
        Returns:
            List of content gap opportunities
        """
        # Extract topics from both
        competitor_topics = set()
        for content in competitor_content:
            topics = self.extract_topics(content, content.get("platform", "instagram"))
            competitor_topics.update(topics)
        
        user_topics = set()
        for content in user_content:
            topics = self.extract_topics(content, content.get("platform", "instagram"))
            user_topics.update(topics)
        
        # Find gaps
        gaps = competitor_topics - user_topics
        
        # Score gaps by frequency in competitor content
        gap_scores = {}
        for gap in gaps:
            count = sum(
                1 for content in competitor_content
                if gap in self.extract_topics(content, content.get("platform", "instagram"))
            )
            gap_scores[gap] = count
        
        # Sort by frequency
        sorted_gaps = sorted(gap_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "topic": gap,
                "frequency": count,
                "opportunity_score": min(count / len(competitor_content) * 100, 100),
            }
            for gap, count in sorted_gaps[:10]  # Top 10 gaps
        ]
    
    def analyze_posting_frequency(
        self,
        content: List[Dict],
    ) -> Dict:
        """Analyze posting frequency patterns.
        
        Args:
            content: List of content items with posted_at timestamps
            
        Returns:
            Posting frequency analysis
        """
        if not content:
            return {
                "posts_per_week": 0,
                "posts_per_day": 0,
                "most_active_days": [],
                "most_active_hours": [],
            }
        
        # Simple analysis (in production, use more sophisticated time series analysis)
        total_posts = len(content)
        
        # Estimate posts per week (assuming content spans ~1 month)
        posts_per_week = total_posts / 4
        posts_per_day = posts_per_week / 7
        
        return {
            "posts_per_week": round(posts_per_week, 1),
            "posts_per_day": round(posts_per_day, 2),
            "most_active_days": ["monday", "wednesday", "friday"],  # Mock
            "most_active_hours": ["18:00", "20:00"],  # Mock
            "consistency_score": 0.85,  # Mock
        }
    
    def generate_steal_idea_brief(
        self,
        content: Dict,
        platform: str,
        virality_score: float,
    ) -> str:
        """Generate "steal the idea, do it better" brief.
        
        Args:
            content: Content data
            platform: Platform name
            virality_score: Calculated virality score
            
        Returns:
            Actionable brief
        """
        topics = self.extract_topics(content, platform)
        
        # Extract content type
        content_type = content.get("type", "post")
        
        # Generate brief
        brief = f"Create a {content_type} about {', '.join(topics[:3]) if topics else 'this topic'}. "
        
        if virality_score > 80:
            brief += "This format is performing exceptionally well. "
        
        # Add platform-specific advice
        if platform == "instagram":
            brief += "Use carousel format for higher engagement. "
        elif platform == "youtube":
            brief += "Keep it under 10 minutes for better retention. "
        elif platform == "tiktok":
            brief += "Hook viewers in first 3 seconds. "
        
        # Add hashtag strategy
        if content.get("hashtags"):
            brief += f"Use similar hashtags: {', '.join(content['hashtags'][:3])}. "
        
        brief += "Add your unique perspective to stand out."
        
        return brief
    
    def analyze_competitor_profile(
        self,
        profile_data: Dict,
    ) -> Dict:
        """Analyze complete competitor profile.
        
        Args:
            profile_data: Profile data from scraper
            
        Returns:
            Complete analysis with insights
        """
        platform = profile_data.get("platform", "instagram")
        followers = profile_data.get("followers", 0)
        content_items = profile_data.get("posts", []) or profile_data.get("videos", [])
        
        if not content_items:
            return {
                "error": "No content found",
                "platform": platform,
            }
        
        # Analyze each content item
        analyzed_content = []
        for content in content_items:
            virality_score = self.calculate_virality_score(content, platform)
            engagement_rate = self.calculate_engagement_rate(content, followers, platform)
            topics = self.extract_topics(content, platform)
            
            analyzed_content.append({
                **content,
                "virality_score": round(virality_score, 2),
                "engagement_rate": round(engagement_rate, 4),
                "topics": topics,
                "steal_idea_brief": self.generate_steal_idea_brief(
                    content, platform, virality_score
                ) if virality_score > 70 else None,
            })
        
        # Sort by virality score
        analyzed_content.sort(key=lambda x: x["virality_score"], reverse=True)
        
        # Calculate aggregate metrics
        avg_virality = sum(c["virality_score"] for c in analyzed_content) / len(analyzed_content)
        avg_engagement = sum(c["engagement_rate"] for c in analyzed_content) / len(analyzed_content)
        
        # Posting frequency
        posting_frequency = self.analyze_posting_frequency(content_items)
        
        # Extract all topics
        all_topics = []
        for content in analyzed_content:
            all_topics.extend(content["topics"])
        
        # Count topic frequency
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "platform": platform,
            "username": profile_data.get("username") or profile_data.get("channel_id"),
            "followers": followers,
            "content_analyzed": len(analyzed_content),
            "avg_virality_score": round(avg_virality, 2),
            "avg_engagement_rate": round(avg_engagement, 4),
            "posting_frequency": posting_frequency,
            "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
            "top_performing_content": analyzed_content[:5],  # Top 5
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
