"""Growth optimization service for maximizing reach and engagement.

Analyzes:
- Hashtag performance and strategy
- Comment engagement patterns
- Caption effectiveness
- CTA (Call-to-Action) optimization
- Cross-platform promotion
- Viral loop detection
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import re
import structlog

log = structlog.get_logger(__name__)


class GrowthOptimizer:
    """Optimize content for maximum growth and engagement."""
    
    # Platform-specific hashtag limits
    HASHTAG_LIMITS = {
        "instagram": 30,
        "tiktok": 100,  # Character limit, not count
        "twitter": 280,  # Character limit
        "linkedin": 3,  # Recommended
        "youtube": 15,  # In description
        "facebook": 2,  # Recommended
    }
    
    # Hashtag size categories (follower count ranges)
    HASHTAG_CATEGORIES = {
        "niche": (0, 10000),  # < 10K posts
        "small": (10000, 100000),  # 10K-100K posts
        "medium": (100000, 500000),  # 100K-500K posts
        "large": (500000, 1000000),  # 500K-1M posts
        "mega": (1000000, float('inf')),  # > 1M posts
    }
    
    # CTA types and their typical conversion rates
    CTA_BENCHMARKS = {
        "follow": {"baseline": 0.02, "good": 0.05, "excellent": 0.10},
        "like": {"baseline": 0.05, "good": 0.10, "excellent": 0.20},
        "comment": {"baseline": 0.01, "good": 0.03, "excellent": 0.08},
        "share": {"baseline": 0.005, "good": 0.02, "excellent": 0.05},
        "save": {"baseline": 0.03, "good": 0.08, "excellent": 0.15},
        "click_link": {"baseline": 0.01, "good": 0.05, "excellent": 0.12},
        "dm": {"baseline": 0.005, "good": 0.02, "excellent": 0.05},
    }
    
    def analyze_hashtag_performance(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Analyze which hashtags drive the most engagement.
        
        Args:
            content_items: List of content items with hashtags and performance
            
        Returns:
            Hashtag performance analysis
        """
        if not content_items:
            return {
                "total_hashtags_analyzed": 0,
                "top_performing_hashtags": [],
                "hashtag_performance": {},
                "recommendations": [],
            }
        
        # Track performance per hashtag
        hashtag_stats = defaultdict(lambda: {
            "usage_count": 0,
            "total_views": 0,
            "total_engagement": 0,
            "avg_engagement_rate": 0.0,
        })
        
        for content in content_items:
            hashtags = content.get("hashtags", [])
            views = content.get("views", 0)
            engagement = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("shares", 0) +
                content.get("saves", 0)
            )
            
            for hashtag in hashtags:
                # Normalize hashtag (remove # if present, lowercase)
                normalized = hashtag.lower().strip().lstrip('#')
                
                hashtag_stats[normalized]["usage_count"] += 1
                hashtag_stats[normalized]["total_views"] += views
                hashtag_stats[normalized]["total_engagement"] += engagement
        
        # Calculate averages
        for hashtag, stats in hashtag_stats.items():
            if stats["usage_count"] > 0:
                stats["avg_views"] = stats["total_views"] / stats["usage_count"]
                stats["avg_engagement"] = stats["total_engagement"] / stats["usage_count"]
                
                if stats["total_views"] > 0:
                    stats["avg_engagement_rate"] = (
                        stats["total_engagement"] / stats["total_views"]
                    )
        
        # Sort by engagement rate
        sorted_hashtags = sorted(
            hashtag_stats.items(),
            key=lambda x: (x[1]["avg_engagement_rate"], x[1]["usage_count"]),
            reverse=True
        )
        
        # Get top 20 performing hashtags
        top_hashtags = [
            {
                "hashtag": f"#{hashtag}",
                "usage_count": stats["usage_count"],
                "avg_views": round(stats.get("avg_views", 0), 2),
                "avg_engagement": round(stats.get("avg_engagement", 0), 2),
                "avg_engagement_rate": round(stats["avg_engagement_rate"], 4),
                "performance_score": round(
                    stats["avg_engagement_rate"] * 100 + 
                    (stats["usage_count"] / len(content_items)) * 10,
                    2
                ),
            }
            for hashtag, stats in sorted_hashtags[:20]
        ]
        
        # Generate recommendations
        recommendations = self._generate_hashtag_recommendations(
            top_hashtags,
            len(content_items)
        )
        
        return {
            "total_hashtags_analyzed": len(hashtag_stats),
            "top_performing_hashtags": top_hashtags,
            "hashtag_performance": dict(sorted_hashtags),
            "recommendations": recommendations,
        }
    
    def _generate_hashtag_recommendations(
        self,
        top_hashtags: List[Dict],
        total_content: int,
    ) -> List[str]:
        """Generate hashtag strategy recommendations."""
        recommendations = []
        
        if not top_hashtags:
            recommendations.append("Start using hashtags to increase discoverability")
            return recommendations
        
        # Check for overused hashtags
        overused = [h for h in top_hashtags if h["usage_count"] / total_content > 0.8]
        if overused:
            recommendations.append(
                f"Diversify hashtags - {overused[0]['hashtag']} used in {overused[0]['usage_count']}/{total_content} posts"
            )
        
        # Check for underperforming hashtags
        if len(top_hashtags) > 5:
            bottom_performers = top_hashtags[-3:]
            if bottom_performers[0]["avg_engagement_rate"] < 0.01:
                recommendations.append(
                    f"Replace low-performing hashtags like {bottom_performers[0]['hashtag']} (engagement: {bottom_performers[0]['avg_engagement_rate']:.2%})"
                )
        
        # Recommend top performers
        if top_hashtags:
            top = top_hashtags[0]
            recommendations.append(
                f"Use {top['hashtag']} more often - highest engagement rate ({top['avg_engagement_rate']:.2%})"
            )
        
        return recommendations
    
    def optimize_hashtag_strategy(
        self,
        platform: str,
        niche_keywords: List[str],
        current_hashtags: List[str],
        performance_data: Dict,
    ) -> Dict:
        """Generate optimized hashtag strategy for a platform.
        
        Args:
            platform: Platform name
            niche_keywords: Creator's niche keywords
            current_hashtags: Currently used hashtags
            performance_data: Historical performance data
            
        Returns:
            Optimized hashtag strategy
        """
        limit = self.HASHTAG_LIMITS.get(platform.lower(), 10)
        
        # Analyze current performance
        top_performers = performance_data.get("top_performing_hashtags", [])[:5]
        
        # Build recommended mix (30% niche, 40% small, 20% medium, 10% large)
        recommended_hashtags = []
        
        # Add top performers
        for hashtag_data in top_performers[:3]:
            recommended_hashtags.append({
                "hashtag": hashtag_data["hashtag"],
                "reason": f"Top performer - {hashtag_data['avg_engagement_rate']:.2%} engagement",
                "category": "proven",
            })
        
        # Add niche-specific hashtags
        for keyword in niche_keywords[:3]:
            hashtag = f"#{keyword.lower().replace(' ', '')}"
            if hashtag not in [h["hashtag"] for h in recommended_hashtags]:
                recommended_hashtags.append({
                    "hashtag": hashtag,
                    "reason": "Niche-specific for targeted reach",
                    "category": "niche",
                })
        
        # Limit to platform maximum
        recommended_hashtags = recommended_hashtags[:limit]
        
        return {
            "platform": platform,
            "recommended_count": len(recommended_hashtags),
            "max_allowed": limit,
            "recommended_hashtags": recommended_hashtags,
            "strategy": {
                "niche_hashtags": [h for h in recommended_hashtags if h["category"] == "niche"],
                "proven_hashtags": [h for h in recommended_hashtags if h["category"] == "proven"],
            },
            "expected_impact": "+30-50% reach improvement",
        }
    
    def analyze_comment_engagement(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Analyze comment engagement patterns.
        
        Args:
            content_items: List of content items with comment data
            
        Returns:
            Comment engagement analysis
        """
        if not content_items:
            return {
                "total_content_analyzed": 0,
                "avg_comments_per_post": 0,
                "comment_rate": 0,
                "best_comment_triggers": [],
            }
        
        total_comments = 0
        total_views = 0
        comment_triggers = []
        
        for content in content_items:
            comments = content.get("comments", 0)
            views = content.get("views", 0)
            caption = content.get("caption", "")
            
            total_comments += comments
            total_views += views
            
            # Detect comment triggers in caption
            if "?" in caption:
                comment_triggers.append("question")
            if any(word in caption.lower() for word in ["comment", "tell me", "let me know", "thoughts"]):
                comment_triggers.append("direct_ask")
            if any(word in caption.lower() for word in ["agree", "disagree", "opinion"]):
                comment_triggers.append("opinion_request")
        
        # Calculate metrics
        avg_comments = total_comments / len(content_items) if content_items else 0
        comment_rate = total_comments / total_views if total_views > 0 else 0
        
        # Count trigger frequency
        trigger_counts = Counter(comment_triggers)
        
        return {
            "total_content_analyzed": len(content_items),
            "total_comments": total_comments,
            "avg_comments_per_post": round(avg_comments, 2),
            "comment_rate": round(comment_rate, 4),
            "best_comment_triggers": [
                {"trigger": trigger, "frequency": count}
                for trigger, count in trigger_counts.most_common(5)
            ],
            "recommendations": self._generate_comment_recommendations(comment_rate),
        }
    
    def _generate_comment_recommendations(self, comment_rate: float) -> List[str]:
        """Generate recommendations to improve comment engagement."""
        recommendations = []
        
        if comment_rate < 0.01:
            recommendations.append("Add questions to your captions to encourage comments")
            recommendations.append("Use 'Comment below' CTAs to prompt engagement")
        elif comment_rate < 0.03:
            recommendations.append("Ask for opinions to spark discussion")
            recommendations.append("Create polls or 'this or that' questions")
        else:
            recommendations.append("Great comment rate! Keep asking engaging questions")
            recommendations.append("Reply to comments within first 30 mins for algorithm boost")
        
        return recommendations
    
    def analyze_cta_effectiveness(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Analyze CTA (Call-to-Action) effectiveness.
        
        Args:
            content_items: List of content items with CTA data
            
        Returns:
            CTA effectiveness analysis
        """
        if not content_items:
            return {
                "ctas_analyzed": 0,
                "cta_performance": {},
                "recommendations": [],
            }
        
        # Detect CTAs in captions
        cta_patterns = {
            "follow": r'\b(follow|subscribe)\b',
            "like": r'\b(like|double tap)\b',
            "comment": r'\b(comment|tell me|let me know)\b',
            "share": r'\b(share|tag|send)\b',
            "save": r'\b(save|bookmark)\b',
            "click_link": r'\b(link|bio|swipe up|click)\b',
            "dm": r'\b(dm|message|inbox)\b',
        }
        
        cta_performance = defaultdict(lambda: {
            "usage_count": 0,
            "total_engagement": 0,
            "avg_engagement_rate": 0.0,
        })
        
        for content in content_items:
            caption = content.get("caption", "").lower()
            views = content.get("views", 0)
            engagement = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("shares", 0) +
                content.get("saves", 0)
            )
            
            # Detect which CTAs are present
            detected_ctas = []
            for cta_type, pattern in cta_patterns.items():
                if re.search(pattern, caption, re.IGNORECASE):
                    detected_ctas.append(cta_type)
            
            # Track performance for each CTA
            for cta in detected_ctas:
                cta_performance[cta]["usage_count"] += 1
                cta_performance[cta]["total_engagement"] += engagement
                
                if views > 0:
                    engagement_rate = engagement / views
                    cta_performance[cta]["avg_engagement_rate"] += engagement_rate
        
        # Calculate averages
        for cta, stats in cta_performance.items():
            if stats["usage_count"] > 0:
                stats["avg_engagement_rate"] = stats["avg_engagement_rate"] / stats["usage_count"]
                
                # Compare to benchmark
                benchmark = self.CTA_BENCHMARKS.get(cta, {})
                if stats["avg_engagement_rate"] >= benchmark.get("excellent", 0.1):
                    stats["performance"] = "excellent"
                elif stats["avg_engagement_rate"] >= benchmark.get("good", 0.05):
                    stats["performance"] = "good"
                else:
                    stats["performance"] = "needs_improvement"
        
        # Sort by performance
        sorted_ctas = sorted(
            cta_performance.items(),
            key=lambda x: x[1]["avg_engagement_rate"],
            reverse=True
        )
        
        # Generate recommendations
        recommendations = self._generate_cta_recommendations(sorted_ctas)
        
        return {
            "ctas_analyzed": len(cta_performance),
            "cta_performance": {
                cta: {
                    "usage_count": stats["usage_count"],
                    "avg_engagement_rate": round(stats["avg_engagement_rate"], 4),
                    "performance": stats.get("performance", "unknown"),
                }
                for cta, stats in sorted_ctas
            },
            "top_performing_cta": sorted_ctas[0][0] if sorted_ctas else None,
            "recommendations": recommendations,
        }
    
    def _generate_cta_recommendations(self, sorted_ctas: List[Tuple]) -> List[str]:
        """Generate CTA optimization recommendations."""
        recommendations = []
        
        if not sorted_ctas:
            recommendations.append("Add clear CTAs to your captions (e.g., 'Save this for later')")
            return recommendations
        
        # Recommend top performer
        if sorted_ctas:
            top_cta, top_stats = sorted_ctas[0]
            recommendations.append(
                f"'{top_cta.replace('_', ' ').title()}' CTA performs best - use it more often"
            )
        
        # Identify underperformers
        if len(sorted_ctas) > 2:
            bottom_cta, bottom_stats = sorted_ctas[-1]
            if bottom_stats["avg_engagement_rate"] < 0.02:
                recommendations.append(
                    f"Replace '{bottom_cta.replace('_', ' ')}' CTA - low engagement ({bottom_stats['avg_engagement_rate']:.2%})"
                )
        
        # General best practices
        recommendations.append("Place CTAs at the end of captions for better visibility")
        recommendations.append("Use action verbs (Save, Share, Comment) for stronger CTAs")
        
        return recommendations
    
    def detect_viral_loops(
        self,
        content_items: List[Dict],
    ) -> Dict:
        """Detect viral loop patterns in content.
        
        Args:
            content_items: List of content items with engagement data
            
        Returns:
            Viral loop analysis
        """
        if not content_items:
            return {
                "viral_content_count": 0,
                "viral_patterns": [],
                "recommendations": [],
            }
        
        # Define viral threshold (engagement rate > 10%)
        viral_threshold = 0.10
        viral_content = []
        
        for content in content_items:
            views = content.get("views", 0)
            engagement = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("shares", 0) +
                content.get("saves", 0)
            )
            
            if views > 0:
                engagement_rate = engagement / views
                
                if engagement_rate >= viral_threshold:
                    viral_content.append({
                        "title": content.get("title", "Untitled"),
                        "engagement_rate": engagement_rate,
                        "shares": content.get("shares", 0),
                        "saves": content.get("saves", 0),
                        "hashtags": content.get("hashtags", []),
                        "content_type": content.get("content_type", "unknown"),
                    })
        
        # Analyze patterns in viral content
        patterns = self._analyze_viral_patterns(viral_content)
        
        return {
            "viral_content_count": len(viral_content),
            "viral_rate": round(len(viral_content) / len(content_items), 3) if content_items else 0,
            "viral_threshold": viral_threshold,
            "viral_content": viral_content[:10],  # Top 10
            "viral_patterns": patterns,
            "recommendations": self._generate_viral_recommendations(patterns),
        }
    
    def _analyze_viral_patterns(self, viral_content: List[Dict]) -> List[Dict]:
        """Analyze common patterns in viral content."""
        if not viral_content:
            return []
        
        patterns = []
        
        # Analyze content types
        content_types = Counter(c["content_type"] for c in viral_content)
        if content_types:
            top_type = content_types.most_common(1)[0]
            patterns.append({
                "pattern": "content_type",
                "value": top_type[0],
                "frequency": top_type[1],
                "insight": f"{top_type[0]} format goes viral most often",
            })
        
        # Analyze hashtags
        all_hashtags = []
        for content in viral_content:
            all_hashtags.extend(content.get("hashtags", []))
        
        if all_hashtags:
            hashtag_counts = Counter(all_hashtags)
            top_hashtag = hashtag_counts.most_common(1)[0]
            patterns.append({
                "pattern": "hashtag",
                "value": top_hashtag[0],
                "frequency": top_hashtag[1],
                "insight": f"{top_hashtag[0]} appears in {top_hashtag[1]} viral posts",
            })
        
        # Analyze share rate
        avg_shares = sum(c["shares"] for c in viral_content) / len(viral_content)
        if avg_shares > 10:
            patterns.append({
                "pattern": "high_shareability",
                "value": round(avg_shares, 1),
                "insight": f"Viral content averages {avg_shares:.0f} shares",
            })
        
        return patterns
    
    def _generate_viral_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Generate recommendations based on viral patterns."""
        recommendations = []
        
        if not patterns:
            recommendations.append("Create shareable content to increase viral potential")
            recommendations.append("Use trending formats and sounds")
            return recommendations
        
        for pattern in patterns:
            if pattern["pattern"] == "content_type":
                recommendations.append(
                    f"Focus on {pattern['value']} format - it goes viral most often"
                )
            elif pattern["pattern"] == "hashtag":
                recommendations.append(
                    f"Use {pattern['value']} hashtag - appears in {pattern['frequency']} viral posts"
                )
            elif pattern["pattern"] == "high_shareability":
                recommendations.append(
                    f"Create more shareable content - viral posts average {pattern['value']} shares"
                )
        
        return recommendations
    
    def calculate_growth_score(
        self,
        hashtag_performance: Dict,
        comment_engagement: Dict,
        cta_effectiveness: Dict,
        viral_loops: Dict,
    ) -> Dict:
        """Calculate overall growth optimization score.
        
        Args:
            hashtag_performance: Hashtag analysis results
            comment_engagement: Comment analysis results
            cta_effectiveness: CTA analysis results
            viral_loops: Viral loop analysis results
            
        Returns:
            Overall growth score and breakdown
        """
        scores = {}
        
        # Hashtag score (0-100)
        if hashtag_performance.get("top_performing_hashtags"):
            top_hashtag = hashtag_performance["top_performing_hashtags"][0]
            hashtag_score = min(top_hashtag["avg_engagement_rate"] * 1000, 100)
        else:
            hashtag_score = 0
        scores["hashtag_strategy"] = round(hashtag_score, 1)
        
        # Comment score (0-100)
        comment_rate = comment_engagement.get("comment_rate", 0)
        comment_score = min(comment_rate * 3000, 100)
        scores["comment_engagement"] = round(comment_score, 1)
        
        # CTA score (0-100)
        if cta_effectiveness.get("cta_performance"):
            cta_rates = [
                stats["avg_engagement_rate"]
                for stats in cta_effectiveness["cta_performance"].values()
            ]
            avg_cta_rate = sum(cta_rates) / len(cta_rates) if cta_rates else 0
            cta_score = min(avg_cta_rate * 500, 100)
        else:
            cta_score = 0
        scores["cta_effectiveness"] = round(cta_score, 1)
        
        # Viral score (0-100)
        viral_rate = viral_loops.get("viral_rate", 0)
        viral_score = min(viral_rate * 500, 100)
        scores["viral_potential"] = round(viral_score, 1)
        
        # Overall score (weighted average)
        overall_score = (
            scores["hashtag_strategy"] * 0.3 +
            scores["comment_engagement"] * 0.25 +
            scores["cta_effectiveness"] * 0.25 +
            scores["viral_potential"] * 0.20
        )
        
        return {
            "overall_score": round(overall_score, 1),
            "score_breakdown": scores,
            "grade": self._get_grade(overall_score),
            "top_strength": max(scores.items(), key=lambda x: x[1])[0] if scores else None,
            "top_weakness": min(scores.items(), key=lambda x: x[1])[0] if scores else None,
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
