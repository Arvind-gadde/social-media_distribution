"""Tips & Tricks provider for platform algorithm insights and growth hacks.

Provides:
- Platform algorithm updates
- Growth hacks
- Format optimization tips
- Engagement strategies
- Best practices
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import structlog

log = structlog.get_logger(__name__)


class TipsProvider:
    """Provide platform-specific tips, tricks, and algorithm insights."""
    
    # Platform-specific tips database
    PLATFORM_TIPS = {
        "instagram": [
            {
                "tip_type": "algorithm_hack",
                "title": "Use 3-5 hashtags instead of 30 for better reach",
                "explanation": "Instagram's 2026 algorithm now penalizes hashtag stuffing. Posts with 3-5 highly relevant hashtags get 15% more reach than those with 30.",
                "expected_impact": "+15% reach",
                "confidence": 0.92,
                "source": "Instagram Creator Blog",
                "date_published": "2026-03-15",
                "platforms": ["instagram"],
                "content_types": ["post", "reel", "carousel"],
            },
            {
                "tip_type": "engagement_hack",
                "title": "Reply to comments within first 30 minutes for algorithm boost",
                "explanation": "Instagram prioritizes posts where creators actively engage. Replying to comments in the first 30 minutes signals high-quality content to the algorithm.",
                "expected_impact": "+35% engagement rate",
                "confidence": 0.88,
                "source": "Social Media Examiner",
                "date_published": "2026-02-20",
                "platforms": ["instagram"],
                "content_types": ["post", "reel", "carousel", "story"],
            },
            {
                "tip_type": "format_optimization",
                "title": "Reels under 15 seconds get 2x more shares",
                "explanation": "Short-form content (7-15 seconds) is more shareable. The algorithm rewards shares heavily, making shorter reels more likely to go viral.",
                "expected_impact": "+100% shares",
                "confidence": 0.85,
                "source": "Instagram Insights Report",
                "date_published": "2026-01-10",
                "platforms": ["instagram"],
                "content_types": ["reel"],
            },
            {
                "tip_type": "posting_strategy",
                "title": "Post carousels for 3x longer dwell time",
                "explanation": "Carousel posts keep users engaged longer as they swipe through. Longer dwell time signals quality content to the algorithm.",
                "expected_impact": "+200% dwell time",
                "confidence": 0.90,
                "source": "Later.com Study",
                "date_published": "2026-02-05",
                "platforms": ["instagram"],
                "content_types": ["carousel"],
            },
        ],
        "youtube": [
            {
                "tip_type": "retention_hack",
                "title": "Add chapter markers to boost watch time by 23%",
                "explanation": "Viewers stay 23% longer on videos with chapters. They can jump to sections they care about, reducing early exits.",
                "expected_impact": "+23% avg watch time",
                "confidence": 0.94,
                "source": "YouTube Creator Academy",
                "date_published": "2026-03-01",
                "platforms": ["youtube"],
                "content_types": ["long_video"],
            },
            {
                "tip_type": "algorithm_hack",
                "title": "First 30 seconds determine 70% of your reach",
                "explanation": "YouTube's algorithm heavily weights early retention. If viewers stay past 30 seconds, your video gets recommended more.",
                "expected_impact": "+70% impressions",
                "confidence": 0.96,
                "source": "YouTube Algorithm Update 2026",
                "date_published": "2026-02-15",
                "platforms": ["youtube"],
                "content_types": ["long_video", "short"],
            },
            {
                "tip_type": "thumbnail_optimization",
                "title": "Faces in thumbnails get 40% more clicks",
                "explanation": "Human faces trigger emotional connection. Thumbnails with expressive faces have significantly higher CTR.",
                "expected_impact": "+40% CTR",
                "confidence": 0.89,
                "source": "VidIQ Study",
                "date_published": "2026-01-20",
                "platforms": ["youtube"],
                "content_types": ["long_video", "short"],
            },
        ],
        "tiktok": [
            {
                "tip_type": "algorithm_hack",
                "title": "Hook viewers in first 1 second for FYP boost",
                "explanation": "TikTok's algorithm measures completion rate. Videos that hook viewers instantly (within 1 second) are 5x more likely to hit FYP.",
                "expected_impact": "+400% FYP reach",
                "confidence": 0.91,
                "source": "TikTok Creator Portal",
                "date_published": "2026-03-10",
                "platforms": ["tiktok"],
                "content_types": ["short_video"],
            },
            {
                "tip_type": "engagement_hack",
                "title": "Ask a question in caption to boost comments by 60%",
                "explanation": "TikTok prioritizes videos with high comment rates. Asking a direct question in the caption drives engagement.",
                "expected_impact": "+60% comments",
                "confidence": 0.87,
                "source": "Hootsuite TikTok Report",
                "date_published": "2026-02-25",
                "platforms": ["tiktok"],
                "content_types": ["short_video"],
            },
            {
                "tip_type": "posting_strategy",
                "title": "Post 3-5 times per day for maximum reach",
                "explanation": "TikTok rewards consistent posting. Accounts posting 3-5x daily see 3x more reach than those posting once daily.",
                "expected_impact": "+200% reach",
                "confidence": 0.83,
                "source": "Later.com TikTok Study",
                "date_published": "2026-01-15",
                "platforms": ["tiktok"],
                "content_types": ["short_video"],
            },
        ],
        "twitter": [
            {
                "tip_type": "engagement_hack",
                "title": "Threads get 10x more engagement than single tweets",
                "explanation": "Twitter's algorithm promotes threads. Breaking content into 3-5 tweet threads dramatically increases visibility.",
                "expected_impact": "+900% engagement",
                "confidence": 0.86,
                "source": "Twitter Creator Newsletter",
                "date_published": "2026-03-05",
                "platforms": ["twitter"],
                "content_types": ["thread", "tweet"],
            },
            {
                "tip_type": "format_optimization",
                "title": "Add images to tweets for 150% more retweets",
                "explanation": "Tweets with images get significantly more engagement. Visual content stands out in the timeline.",
                "expected_impact": "+150% retweets",
                "confidence": 0.90,
                "source": "Buffer Social Study",
                "date_published": "2026-02-10",
                "platforms": ["twitter"],
                "content_types": ["tweet"],
            },
        ],
        "linkedin": [
            {
                "tip_type": "algorithm_hack",
                "title": "Native documents get 3x more reach than links",
                "explanation": "LinkedIn penalizes external links. Upload PDFs/documents natively instead of linking out.",
                "expected_impact": "+200% reach",
                "confidence": 0.93,
                "source": "LinkedIn Algorithm Update",
                "date_published": "2026-03-20",
                "platforms": ["linkedin"],
                "content_types": ["post", "article"],
            },
            {
                "tip_type": "engagement_hack",
                "title": "Comment on your own post within 1 hour to boost visibility",
                "explanation": "LinkedIn's algorithm rewards early engagement. Adding a thoughtful comment on your own post signals quality content.",
                "expected_impact": "+45% impressions",
                "confidence": 0.84,
                "source": "LinkedIn Creator Mode Guide",
                "date_published": "2026-02-28",
                "platforms": ["linkedin"],
                "content_types": ["post"],
            },
        ],
    }
    
    def get_tips_for_platform(
        self,
        platform: str,
        content_type: Optional[str] = None,
        min_confidence: float = 0.80,
    ) -> List[Dict]:
        """Get tips for a specific platform.
        
        Args:
            platform: Platform name (instagram, youtube, tiktok, etc.)
            content_type: Optional content type filter
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of tips matching criteria
        """
        platform_lower = platform.lower()
        
        if platform_lower not in self.PLATFORM_TIPS:
            log.warning("tips_provider.unknown_platform", platform=platform)
            return []
        
        tips = self.PLATFORM_TIPS[platform_lower]
        
        # Filter by content type if specified
        if content_type:
            tips = [
                tip for tip in tips
                if content_type in tip.get("content_types", [])
            ]
        
        # Filter by confidence
        tips = [
            tip for tip in tips
            if tip.get("confidence", 0) >= min_confidence
        ]
        
        # Sort by confidence (highest first)
        tips.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return tips
    
    def get_all_tips(
        self,
        platforms: Optional[List[str]] = None,
        min_confidence: float = 0.80,
    ) -> List[Dict]:
        """Get tips across multiple platforms.
        
        Args:
            platforms: List of platforms to include (None = all)
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of tips sorted by confidence
        """
        if platforms is None:
            platforms = list(self.PLATFORM_TIPS.keys())
        
        all_tips = []
        for platform in platforms:
            platform_tips = self.get_tips_for_platform(
                platform=platform,
                min_confidence=min_confidence,
            )
            all_tips.extend(platform_tips)
        
        # Sort by confidence
        all_tips.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return all_tips
    
    def get_recent_tips(
        self,
        days: int = 30,
        platforms: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get tips published in the last N days.
        
        Args:
            days: Number of days to look back
            platforms: List of platforms to include
            
        Returns:
            List of recent tips
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        all_tips = self.get_all_tips(platforms=platforms)
        
        recent_tips = []
        for tip in all_tips:
            date_str = tip.get("date_published")
            if date_str:
                try:
                    tip_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                    if tip_date >= cutoff_date:
                        recent_tips.append(tip)
                except (ValueError, AttributeError):
                    pass
        
        return recent_tips
    
    def get_tips_by_type(
        self,
        tip_type: str,
        platforms: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get tips of a specific type.
        
        Args:
            tip_type: Type of tip (algorithm_hack, engagement_hack, etc.)
            platforms: List of platforms to include
            
        Returns:
            List of tips matching type
        """
        all_tips = self.get_all_tips(platforms=platforms)
        
        filtered_tips = [
            tip for tip in all_tips
            if tip.get("tip_type") == tip_type
        ]
        
        return filtered_tips
    
    def calculate_impact_score(self, tip: Dict) -> float:
        """Calculate overall impact score for a tip.
        
        Args:
            tip: Tip dictionary
            
        Returns:
            Impact score (0-1)
        """
        confidence = tip.get("confidence", 0.5)
        
        # Parse expected impact
        impact_str = tip.get("expected_impact", "+0%")
        try:
            # Extract percentage from string like "+15% reach"
            impact_pct = float(impact_str.replace("%", "").replace("+", "").split()[0])
            # Normalize to 0-1 scale (cap at 500%)
            impact_normalized = min(impact_pct / 500, 1.0)
        except (ValueError, IndexError):
            impact_normalized = 0.5
        
        # Weighted average (confidence 60%, impact 40%)
        impact_score = (confidence * 0.6) + (impact_normalized * 0.4)
        
        return round(impact_score, 3)
    
    def get_top_tips(
        self,
        platforms: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Get top tips by impact score.
        
        Args:
            platforms: List of platforms to include
            limit: Maximum number of tips to return
            
        Returns:
            List of top tips with impact scores
        """
        all_tips = self.get_all_tips(platforms=platforms)
        
        # Add impact scores
        for tip in all_tips:
            tip["impact_score"] = self.calculate_impact_score(tip)
        
        # Sort by impact score
        all_tips.sort(key=lambda x: x["impact_score"], reverse=True)
        
        return all_tips[:limit]
