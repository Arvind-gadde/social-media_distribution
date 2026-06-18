"""Virality prediction service for scoring content before publishing.

Analyzes 12 virality signals:
1. Hook strength (first 3 seconds)
2. Emotional resonance
3. Shareability factor
4. Trend alignment
5. Caption engagement potential
6. Hashtag reach
7. Platform fit
8. Posting time alignment
9. Content uniqueness
10. CTA strength
11. Visual quality estimate
12. Audio quality estimate
"""
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime
import structlog

log = structlog.get_logger(__name__)


class ViralityPredictor:
    """Predict content virality before publishing."""
    
    # Signal weights (sum to 1.0)
    SIGNAL_WEIGHTS = {
        "hook_strength": 0.15,
        "emotional_resonance": 0.12,
        "shareability": 0.10,
        "trend_alignment": 0.10,
        "caption_engagement": 0.08,
        "hashtag_reach": 0.08,
        "platform_fit": 0.08,
        "posting_time": 0.08,
        "content_uniqueness": 0.07,
        "cta_strength": 0.06,
        "visual_quality": 0.05,
        "audio_quality": 0.03,
    }
    
    # Hook patterns that typically perform well
    STRONG_HOOK_PATTERNS = [
        r"^(you won't believe|you'll never guess|this is insane)",
        r"^(watch this|wait for it|look at this)",
        r"^(here's why|here's how|this is how)",
        r"^(the secret to|the truth about|nobody tells you)",
        r"^(\d+ (ways|tips|tricks|secrets|hacks))",
        r"^(stop|don't|never) (doing|making|saying)",
    ]
    
    # Emotional trigger words
    EMOTIONAL_TRIGGERS = {
        "positive": ["amazing", "incredible", "awesome", "love", "beautiful", "perfect", "best"],
        "negative": ["shocking", "terrible", "worst", "hate", "awful", "disaster", "fail"],
        "curiosity": ["secret", "hidden", "revealed", "truth", "nobody", "never", "always"],
        "urgency": ["now", "today", "immediately", "urgent", "quick", "fast", "hurry"],
        "social": ["everyone", "nobody", "people", "you", "we", "together", "share"],
    }
    
    # Shareability indicators
    SHAREABILITY_INDICATORS = [
        "tag someone", "send this to", "share with", "show this to",
        "relatable", "mood", "same", "me too",
        "tutorial", "how to", "guide", "tips",
        "funny", "hilarious", "lol", "lmao",
    ]
    
    def predict_virality(
        self,
        content: Dict,
        platform: str,
        historical_performance: Optional[Dict] = None,
        trending_topics: Optional[List[str]] = None,
    ) -> Dict:
        """Predict virality score for content before publishing.
        
        Args:
            content: Content data (title, caption, hashtags, etc.)
            platform: Target platform
            historical_performance: Optional historical data for this creator
            trending_topics: Optional list of currently trending topics
            
        Returns:
            Virality prediction with scores and recommendations
        """
        # Calculate each signal
        signals = {}
        
        signals["hook_strength"] = self.score_hook_strength(
            content.get("title", ""),
            content.get("caption", ""),
        )
        
        signals["emotional_resonance"] = self.score_emotional_resonance(
            content.get("caption", ""),
        )
        
        signals["shareability"] = self.score_shareability(
            content.get("caption", ""),
            content.get("content_type", ""),
        )
        
        signals["trend_alignment"] = self.score_trend_alignment(
            content.get("hashtags", []),
            content.get("caption", ""),
            trending_topics or [],
        )
        
        signals["caption_engagement"] = self.score_caption_engagement(
            content.get("caption", ""),
        )
        
        signals["hashtag_reach"] = self.score_hashtag_reach(
            content.get("hashtags", []),
            platform,
        )
        
        signals["platform_fit"] = self.score_platform_fit(
            content.get("content_type", ""),
            platform,
        )
        
        signals["posting_time"] = self.score_posting_time(
            content.get("scheduled_at"),
            platform,
        )
        
        signals["content_uniqueness"] = self.score_content_uniqueness(
            content.get("title", ""),
            content.get("caption", ""),
            historical_performance,
        )
        
        signals["cta_strength"] = self.score_cta_strength(
            content.get("caption", ""),
        )
        
        signals["visual_quality"] = self.score_visual_quality(
            content.get("has_thumbnail", False),
            content.get("media_count", 0),
        )
        
        signals["audio_quality"] = self.score_audio_quality(
            content.get("has_audio", False),
            content.get("content_type", ""),
        )
        
        # Calculate weighted overall score
        overall_score = sum(
            signals[signal] * self.SIGNAL_WEIGHTS[signal]
            for signal in signals
        )
        
        # Generate improvements
        improvements = self._generate_improvements(signals)
        
        # Predict outcome range
        predicted_range = self._predict_outcome_range(
            overall_score,
            historical_performance,
        )
        
        return {
            "overall_score": round(overall_score, 3),
            "grade": self._get_grade(overall_score),
            "signals": {k: round(v, 3) for k, v in signals.items()},
            "top_strengths": self._get_top_signals(signals, top_n=3, reverse=True),
            "top_weaknesses": self._get_top_signals(signals, top_n=3, reverse=False),
            "improvements": improvements,
            "predicted_range": predicted_range,
            "confidence": self._calculate_confidence(signals, historical_performance),
        }
    
    def score_hook_strength(self, title: str, caption: str) -> float:
        """Score the strength of the opening hook (0-1)."""
        text = (title + " " + caption).lower()
        
        if not text.strip():
            return 0.3  # Neutral score for missing hook
        
        score = 0.5  # Base score
        
        # Check for strong hook patterns
        for pattern in self.STRONG_HOOK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                break
        
        # Check for numbers (specific numbers perform well)
        if re.search(r'\b\d+\b', text[:100]):
            score += 0.1
        
        # Check for questions (engage curiosity)
        if '?' in text[:100]:
            score += 0.1
        
        # Check for power words in first 50 chars
        first_50 = text[:50]
        power_words = ["secret", "truth", "never", "always", "everyone", "nobody"]
        if any(word in first_50 for word in power_words):
            score += 0.1
        
        return min(score, 1.0)
    
    def score_emotional_resonance(self, caption: str) -> float:
        """Score emotional impact of content (0-1)."""
        if not caption:
            return 0.4
        
        caption_lower = caption.lower()
        score = 0.4  # Base score
        
        # Count emotional triggers by category
        emotion_counts = {
            category: sum(1 for word in words if word in caption_lower)
            for category, words in self.EMOTIONAL_TRIGGERS.items()
        }
        
        # Reward diverse emotional triggers
        categories_hit = sum(1 for count in emotion_counts.values() if count > 0)
        score += categories_hit * 0.12
        
        # Bonus for strong emotional words
        total_triggers = sum(emotion_counts.values())
        if total_triggers >= 3:
            score += 0.1
        
        return min(score, 1.0)
    
    def score_shareability(self, caption: str, content_type: str) -> float:
        """Score how shareable the content is (0-1)."""
        if not caption:
            return 0.4
        
        caption_lower = caption.lower()
        score = 0.4  # Base score
        
        # Check for shareability indicators
        share_count = sum(
            1 for indicator in self.SHAREABILITY_INDICATORS
            if indicator in caption_lower
        )
        score += min(share_count * 0.15, 0.3)
        
        # Content type bonus
        shareable_types = ["tutorial", "tips", "how_to", "funny", "inspirational"]
        if content_type in shareable_types:
            score += 0.15
        
        # Check for "tag" or "share" CTAs
        if any(word in caption_lower for word in ["tag", "share", "send"]):
            score += 0.15
        
        return min(score, 1.0)
    
    def score_trend_alignment(
        self,
        hashtags: List[str],
        caption: str,
        trending_topics: List[str],
    ) -> float:
        """Score alignment with current trends (0-1)."""
        if not trending_topics:
            return 0.5  # Neutral if no trend data
        
        score = 0.3  # Base score
        
        # Check hashtags against trends
        hashtag_text = " ".join(hashtags).lower()
        trend_matches = sum(
            1 for trend in trending_topics
            if trend.lower() in hashtag_text or trend.lower() in caption.lower()
        )
        
        if trend_matches > 0:
            score += min(trend_matches * 0.2, 0.5)
        
        # Bonus for multiple trend alignment
        if trend_matches >= 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def score_caption_engagement(self, caption: str) -> float:
        """Score caption's potential to drive engagement (0-1)."""
        if not caption:
            return 0.3
        
        score = 0.4  # Base score
        
        # Check for questions
        question_count = caption.count('?')
        score += min(question_count * 0.1, 0.2)
        
        # Check for engagement prompts
        engagement_words = ["comment", "tell me", "let me know", "thoughts", "opinion"]
        if any(word in caption.lower() for word in engagement_words):
            score += 0.2
        
        # Check for emojis (rough estimate)
        emoji_count = sum(1 for char in caption if ord(char) > 127)
        if emoji_count > 0:
            score += 0.1
        
        # Optimal length (not too short, not too long)
        length = len(caption)
        if 50 <= length <= 300:
            score += 0.1
        
        return min(score, 1.0)
    
    def score_hashtag_reach(self, hashtags: List[str], platform: str) -> float:
        """Score hashtag strategy for reach (0-1)."""
        if not hashtags:
            return 0.3
        
        score = 0.4  # Base score
        
        # Optimal hashtag count by platform
        optimal_counts = {
            "instagram": (10, 20),
            "tiktok": (3, 5),
            "twitter": (1, 2),
            "linkedin": (3, 5),
        }
        
        optimal_range = optimal_counts.get(platform, (3, 10))
        hashtag_count = len(hashtags)
        
        # Score based on count
        if optimal_range[0] <= hashtag_count <= optimal_range[1]:
            score += 0.3
        elif hashtag_count < optimal_range[0]:
            score += 0.1
        
        # Bonus for mix of sizes (niche + popular)
        if hashtag_count >= 5:
            score += 0.2
        
        # Check for branded hashtag
        if any('#' in tag for tag in hashtags):
            score += 0.1
        
        return min(score, 1.0)
    
    def score_platform_fit(self, content_type: str, platform: str) -> float:
        """Score how well content fits the platform (0-1)."""
        # Platform-content type fit matrix
        fit_matrix = {
            "instagram": {
                "reel": 0.95,
                "carousel": 0.85,
                "post": 0.75,
                "story": 0.70,
            },
            "tiktok": {
                "short_video": 0.95,
                "reel": 0.90,
            },
            "youtube": {
                "long_video": 0.95,
                "short": 0.85,
            },
            "twitter": {
                "thread": 0.90,
                "post": 0.85,
            },
            "linkedin": {
                "article": 0.90,
                "post": 0.85,
                "carousel": 0.80,
            },
        }
        
        platform_fits = fit_matrix.get(platform, {})
        return platform_fits.get(content_type, 0.6)  # Default moderate fit
    
    def score_posting_time(self, scheduled_at: Optional[str], platform: str) -> float:
        """Score posting time alignment with optimal times (0-1)."""
        if not scheduled_at:
            return 0.5  # Neutral if no schedule
        
        try:
            if isinstance(scheduled_at, str):
                dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            else:
                dt = scheduled_at
            
            hour = dt.hour
            day = dt.weekday()  # 0=Monday, 6=Sunday
            
            # Platform-specific optimal times (simplified)
            optimal_hours = {
                "instagram": [11, 13, 18, 19, 20, 21],
                "tiktok": [6, 10, 19, 22],
                "youtube": [12, 14, 15, 18],
                "twitter": [8, 12, 17],
                "linkedin": [7, 12, 17],
            }
            
            platform_hours = optimal_hours.get(platform, [12, 18, 20])
            
            # Score based on hour
            if hour in platform_hours:
                score = 0.9
            elif hour in [h-1 for h in platform_hours] or hour in [h+1 for h in platform_hours]:
                score = 0.7
            else:
                score = 0.5
            
            # Weekday bonus for most platforms
            if day < 5 and platform != "youtube":  # Weekday
                score += 0.1
            elif day >= 5 and platform == "youtube":  # Weekend for YouTube
                score += 0.1
            
            return min(score, 1.0)
        
        except:
            return 0.5
    
    def score_content_uniqueness(
        self,
        title: str,
        caption: str,
        historical_performance: Optional[Dict],
    ) -> float:
        """Score content uniqueness vs past content (0-1)."""
        if not historical_performance:
            return 0.7  # Assume unique if no history
        
        # Simple uniqueness check (in production, use embeddings)
        past_titles = historical_performance.get("past_titles", [])
        
        if not past_titles:
            return 0.7
        
        # Check for exact duplicates
        if title in past_titles:
            return 0.2
        
        # Check for similar titles (simple word overlap)
        title_words = set(title.lower().split())
        max_overlap = 0
        
        for past_title in past_titles:
            past_words = set(past_title.lower().split())
            if title_words and past_words:
                overlap = len(title_words & past_words) / len(title_words | past_words)
                max_overlap = max(max_overlap, overlap)
        
        # Score inversely proportional to overlap
        score = 1.0 - (max_overlap * 0.6)
        return max(score, 0.3)
    
    def score_cta_strength(self, caption: str) -> float:
        """Score CTA (Call-to-Action) strength (0-1)."""
        if not caption:
            return 0.3
        
        caption_lower = caption.lower()
        score = 0.4  # Base score
        
        # Strong CTAs
        strong_ctas = ["save", "share", "comment", "follow", "subscribe", "click", "dm"]
        cta_count = sum(1 for cta in strong_ctas if cta in caption_lower)
        
        if cta_count > 0:
            score += 0.3
        
        # Action verbs
        action_verbs = ["get", "learn", "discover", "find", "try", "watch", "see"]
        if any(verb in caption_lower for verb in action_verbs):
            score += 0.2
        
        # Urgency words
        urgency = ["now", "today", "limited", "don't miss"]
        if any(word in caption_lower for word in urgency):
            score += 0.1
        
        return min(score, 1.0)
    
    def score_visual_quality(self, has_thumbnail: bool, media_count: int) -> float:
        """Score visual quality estimate (0-1)."""
        score = 0.5  # Base score
        
        if has_thumbnail:
            score += 0.3
        
        if media_count > 0:
            score += 0.2
        
        # Bonus for multiple media (carousel)
        if media_count > 1:
            score += 0.1
        
        return min(score, 1.0)
    
    def score_audio_quality(self, has_audio: bool, content_type: str) -> float:
        """Score audio quality estimate (0-1)."""
        score = 0.5  # Base score
        
        if has_audio:
            score += 0.3
        
        # Audio is critical for video content
        if content_type in ["reel", "short_video", "long_video"] and has_audio:
            score += 0.2
        
        return min(score, 1.0)
    
    def _generate_improvements(self, signals: Dict[str, float]) -> List[str]:
        """Generate improvement recommendations based on weak signals."""
        improvements = []
        
        # Sort signals by score (lowest first)
        sorted_signals = sorted(signals.items(), key=lambda x: x[1])
        
        # Generate recommendations for bottom 3 signals
        for signal, score in sorted_signals[:3]:
            if score < 0.6:
                improvement = self._get_improvement_for_signal(signal, score)
                if improvement:
                    improvements.append(improvement)
        
        return improvements
    
    def _get_improvement_for_signal(self, signal: str, score: float) -> Optional[str]:
        """Get specific improvement recommendation for a signal."""
        recommendations = {
            "hook_strength": "Strengthen your opening hook - use numbers, questions, or power words in the first line",
            "emotional_resonance": "Add more emotional triggers - use words that evoke curiosity, urgency, or social proof",
            "shareability": "Make it more shareable - add 'tag someone' or 'share this' CTAs",
            "trend_alignment": "Align with current trends - use trending hashtags or topics",
            "caption_engagement": "Improve caption engagement - ask questions or prompt comments",
            "hashtag_reach": "Optimize hashtags - use 10-20 hashtags on Instagram, mix niche and popular",
            "platform_fit": "Choose better content format for this platform",
            "posting_time": "Post at optimal times - check your audience activity patterns",
            "content_uniqueness": "Make content more unique - avoid repeating past topics",
            "cta_strength": "Add stronger CTA - use action verbs like 'Save', 'Share', 'Comment'",
            "visual_quality": "Improve visuals - add custom thumbnail or more media",
            "audio_quality": "Enhance audio - add music or voiceover for video content",
        }
        
        return recommendations.get(signal)
    
    def _predict_outcome_range(
        self,
        overall_score: float,
        historical_performance: Optional[Dict],
    ) -> Dict:
        """Predict likely outcome range based on score."""
        # Base predictions (can be calibrated with historical data)
        if historical_performance:
            avg_views = historical_performance.get("avg_views", 1000)
            avg_engagement_rate = historical_performance.get("avg_engagement_rate", 0.05)
        else:
            avg_views = 1000
            avg_engagement_rate = 0.05
        
        # Multiply by score factor
        score_multiplier = 0.5 + (overall_score * 1.5)  # 0.5x to 2.0x
        
        predicted_views = int(avg_views * score_multiplier)
        predicted_engagement = avg_engagement_rate * score_multiplier
        
        return {
            "views_min": int(predicted_views * 0.7),
            "views_max": int(predicted_views * 1.5),
            "views_likely": predicted_views,
            "engagement_rate": round(predicted_engagement, 4),
            "confidence": "medium" if historical_performance else "low",
        }
    
    def _calculate_confidence(
        self,
        signals: Dict[str, float],
        historical_performance: Optional[Dict],
    ) -> str:
        """Calculate prediction confidence level."""
        # Check signal consistency
        signal_values = list(signals.values())
        avg_signal = sum(signal_values) / len(signal_values)
        variance = sum((s - avg_signal) ** 2 for s in signal_values) / len(signal_values)
        
        # Low variance = high confidence
        if variance < 0.02:
            confidence = "high"
        elif variance < 0.05:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Reduce confidence if no historical data
        if not historical_performance:
            if confidence == "high":
                confidence = "medium"
            elif confidence == "medium":
                confidence = "low"
        
        return confidence
    
    def _get_top_signals(
        self,
        signals: Dict[str, float],
        top_n: int = 3,
        reverse: bool = True,
    ) -> List[Dict]:
        """Get top N signals (strengths or weaknesses)."""
        sorted_signals = sorted(
            signals.items(),
            key=lambda x: x[1],
            reverse=reverse
        )
        
        return [
            {
                "signal": signal.replace('_', ' ').title(),
                "score": round(score, 3),
            }
            for signal, score in sorted_signals[:top_n]
        ]
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.9:
            return "A+"
        elif score >= 0.85:
            return "A"
        elif score >= 0.80:
            return "A-"
        elif score >= 0.75:
            return "B+"
        elif score >= 0.70:
            return "B"
        elif score >= 0.65:
            return "B-"
        elif score >= 0.60:
            return "C+"
        elif score >= 0.55:
            return "C"
        elif score >= 0.50:
            return "C-"
        else:
            return "D"
