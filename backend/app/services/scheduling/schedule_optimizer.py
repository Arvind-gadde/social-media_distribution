"""Schedule optimization service for determining optimal posting times.

Analyzes:
- Audience activity patterns
- Platform peak traffic times
- Competitor posting schedules
- Content type performance by time
- Timezone considerations
"""
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
from collections import Counter, defaultdict
import structlog

log = structlog.get_logger(__name__)


class ScheduleOptimizer:
    """Optimize posting schedules based on audience and platform data."""
    
    # Platform-specific peak times (general data, can be personalized)
    PLATFORM_PEAK_TIMES = {
        "instagram": {
            "weekdays": ["tuesday", "wednesday", "thursday"],
            "times": ["11:00", "13:00", "19:00", "21:00"],
            "timezone": "UTC",
        },
        "youtube": {
            "weekdays": ["friday", "saturday", "sunday"],
            "times": ["12:00", "15:00", "18:00"],
            "timezone": "UTC",
        },
        "tiktok": {
            "weekdays": ["tuesday", "thursday", "friday"],
            "times": ["06:00", "10:00", "19:00", "22:00"],
            "timezone": "UTC",
        },
        "twitter": {
            "weekdays": ["monday", "tuesday", "wednesday"],
            "times": ["08:00", "12:00", "17:00"],
            "timezone": "UTC",
        },
        "linkedin": {
            "weekdays": ["tuesday", "wednesday", "thursday"],
            "times": ["07:00", "12:00", "17:00"],
            "timezone": "UTC",
        },
        "facebook": {
            "weekdays": ["wednesday", "thursday", "friday"],
            "times": ["13:00", "15:00", "19:00"],
            "timezone": "UTC",
        },
    }
    
    # Content type modifiers (some content types perform better at different times)
    CONTENT_TYPE_MODIFIERS = {
        "educational": {"morning_boost": 1.2, "evening_boost": 0.9},
        "entertainment": {"morning_boost": 0.8, "evening_boost": 1.3},
        "news": {"morning_boost": 1.4, "evening_boost": 0.7},
        "inspirational": {"morning_boost": 1.3, "evening_boost": 1.0},
        "promotional": {"morning_boost": 0.9, "evening_boost": 1.1},
    }
    
    def analyze_audience_activity(
        self,
        content_history: List[Dict],
    ) -> Dict:
        """Analyze when audience is most active based on content performance.
        
        Args:
            content_history: List of content items with timestamps and engagement
            
        Returns:
            Activity analysis with peak hours and days
        """
        if not content_history:
            return {
                "peak_hours": [],
                "peak_days": [],
                "activity_by_hour": {},
                "activity_by_day": {},
            }
        
        # Track engagement by hour and day
        engagement_by_hour = defaultdict(list)
        engagement_by_day = defaultdict(list)
        
        for content in content_history:
            published_at = content.get("published_at")
            if not published_at:
                continue
            
            # Parse datetime
            if isinstance(published_at, str):
                try:
                    dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    continue
            else:
                dt = published_at
            
            # Calculate engagement rate
            views = content.get("views", 0)
            engagement = (
                content.get("likes", 0) +
                content.get("comments", 0) +
                content.get("shares", 0)
            )
            
            engagement_rate = engagement / views if views > 0 else 0
            
            # Track by hour and day
            hour = dt.hour
            day = dt.strftime("%A").lower()
            
            engagement_by_hour[hour].append(engagement_rate)
            engagement_by_day[day].append(engagement_rate)
        
        # Calculate average engagement by hour
        avg_by_hour = {
            hour: sum(rates) / len(rates)
            for hour, rates in engagement_by_hour.items()
            if rates
        }
        
        # Calculate average engagement by day
        avg_by_day = {
            day: sum(rates) / len(rates)
            for day, rates in engagement_by_day.items()
            if rates
        }
        
        # Find peak hours (top 3)
        peak_hours = sorted(
            avg_by_hour.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Find peak days (top 3)
        peak_days = sorted(
            avg_by_day.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "peak_hours": [f"{hour:02d}:00" for hour, _ in peak_hours],
            "peak_days": [day for day, _ in peak_days],
            "activity_by_hour": avg_by_hour,
            "activity_by_day": avg_by_day,
            "total_content_analyzed": len(content_history),
        }
    
    def get_platform_optimal_times(
        self,
        platform: str,
        content_type: Optional[str] = None,
    ) -> Dict:
        """Get optimal posting times for a platform.
        
        Args:
            platform: Platform name (instagram, youtube, etc.)
            content_type: Optional content type for time adjustments
            
        Returns:
            Optimal times for the platform
        """
        platform_data = self.PLATFORM_PEAK_TIMES.get(
            platform.lower(),
            self.PLATFORM_PEAK_TIMES["instagram"]  # Default fallback
        )
        
        result = {
            "platform": platform,
            "best_days": platform_data["weekdays"],
            "best_times": platform_data["times"],
            "timezone": platform_data["timezone"],
            "content_type": content_type,
        }
        
        # Apply content type modifiers if provided
        if content_type and content_type in self.CONTENT_TYPE_MODIFIERS:
            modifiers = self.CONTENT_TYPE_MODIFIERS[content_type]
            result["modifiers"] = modifiers
            result["reasoning"] = f"{content_type.title()} content performs better "
            
            if modifiers["morning_boost"] > 1.0:
                result["reasoning"] += "in the morning"
            elif modifiers["evening_boost"] > 1.0:
                result["reasoning"] += "in the evening"
            else:
                result["reasoning"] += "throughout the day"
        
        return result
    
    def analyze_competitor_schedule(
        self,
        competitor_posts: List[Dict],
    ) -> Dict:
        """Analyze when competitors post to avoid clashing.
        
        Args:
            competitor_posts: List of competitor posts with timestamps
            
        Returns:
            Competitor posting pattern analysis
        """
        if not competitor_posts:
            return {
                "competitor_peak_hours": [],
                "competitor_peak_days": [],
                "avoid_times": [],
            }
        
        # Track posting times
        posting_hours = []
        posting_days = []
        
        for post in competitor_posts:
            posted_at = post.get("posted_at") or post.get("published_at")
            if not posted_at:
                continue
            
            # Parse datetime
            if isinstance(posted_at, str):
                try:
                    dt = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                except:
                    continue
            else:
                dt = posted_at
            
            posting_hours.append(dt.hour)
            posting_days.append(dt.strftime("%A").lower())
        
        # Count frequency
        hour_counts = Counter(posting_hours)
        day_counts = Counter(posting_days)
        
        # Find most common times (to avoid)
        top_hours = hour_counts.most_common(3)
        top_days = day_counts.most_common(3)
        
        # Times to avoid (when competitors post most)
        avoid_times = [f"{hour:02d}:00" for hour, _ in top_hours]
        
        return {
            "competitor_peak_hours": [f"{hour:02d}:00" for hour, _ in top_hours],
            "competitor_peak_days": [day for day, _ in top_days],
            "avoid_times": avoid_times,
            "total_posts_analyzed": len(competitor_posts),
        }
    
    def calculate_optimal_schedule(
        self,
        platform: str,
        audience_activity: Dict,
        competitor_schedule: Optional[Dict] = None,
        content_type: Optional[str] = None,
        timezone: str = "UTC",
    ) -> Dict:
        """Calculate optimal posting schedule combining all factors.
        
        Args:
            platform: Platform name
            audience_activity: Audience activity analysis
            competitor_schedule: Optional competitor schedule analysis
            content_type: Optional content type
            timezone: User's timezone
            
        Returns:
            Optimal posting schedule with reasoning
        """
        # Get platform defaults
        platform_optimal = self.get_platform_optimal_times(platform, content_type)
        
        # Combine audience data with platform data
        if audience_activity.get("peak_hours"):
            # Use audience data if available
            best_times = audience_activity["peak_hours"]
            best_days = audience_activity["peak_days"]
            reasoning = f"Based on your audience activity patterns"
        else:
            # Fall back to platform defaults
            best_times = platform_optimal["best_times"]
            best_days = platform_optimal["best_days"]
            reasoning = f"Based on {platform.title()} platform trends"
        
        # Avoid competitor clash times if provided
        if competitor_schedule and competitor_schedule.get("avoid_times"):
            avoid_times = set(competitor_schedule["avoid_times"])
            # Filter out times that clash with competitors
            best_times = [t for t in best_times if t not in avoid_times]
            
            if not best_times:
                # If all times clash, use platform defaults
                best_times = platform_optimal["best_times"]
            else:
                reasoning += f". Avoiding competitor peak times"
        
        # Calculate posting frequency recommendation
        frequency = self._calculate_posting_frequency(platform)
        
        return {
            "platform": platform,
            "best_days": best_days[:3],  # Top 3 days
            "best_times": best_times[:3],  # Top 3 times
            "timezone": timezone,
            "reasoning": reasoning,
            "recommended_frequency": frequency,
            "content_type": content_type,
        }
    
    def _calculate_posting_frequency(self, platform: str) -> Dict:
        """Calculate recommended posting frequency for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Frequency recommendations
        """
        # Platform-specific frequency recommendations
        frequencies = {
            "instagram": {
                "posts_per_week": 5,
                "posts_per_day": 0.7,
                "optimal_gap_hours": 24,
            },
            "youtube": {
                "posts_per_week": 2,
                "posts_per_day": 0.3,
                "optimal_gap_hours": 72,
            },
            "tiktok": {
                "posts_per_week": 7,
                "posts_per_day": 1.0,
                "optimal_gap_hours": 12,
            },
            "twitter": {
                "posts_per_week": 14,
                "posts_per_day": 2.0,
                "optimal_gap_hours": 4,
            },
            "linkedin": {
                "posts_per_week": 3,
                "posts_per_day": 0.4,
                "optimal_gap_hours": 48,
            },
            "facebook": {
                "posts_per_week": 4,
                "posts_per_day": 0.6,
                "optimal_gap_hours": 36,
            },
        }
        
        return frequencies.get(
            platform.lower(),
            {"posts_per_week": 5, "posts_per_day": 0.7, "optimal_gap_hours": 24}
        )
    
    def generate_weekly_schedule(
        self,
        platforms: List[str],
        audience_activity: Dict,
        timezone: str = "UTC",
    ) -> Dict:
        """Generate a complete weekly posting schedule.
        
        Args:
            platforms: List of platforms to schedule for
            audience_activity: Audience activity analysis
            timezone: User's timezone
            
        Returns:
            Weekly schedule with specific posting slots
        """
        weekly_schedule = {}
        
        for platform in platforms:
            optimal = self.calculate_optimal_schedule(
                platform=platform,
                audience_activity=audience_activity,
                timezone=timezone,
            )
            
            # Generate specific time slots
            frequency = optimal["recommended_frequency"]
            posts_per_week = frequency["posts_per_week"]
            
            # Distribute posts across best days and times
            time_slots = []
            days = optimal["best_days"]
            times = optimal["best_times"]
            
            # Create slots by cycling through days and times
            slot_count = 0
            day_idx = 0
            time_idx = 0
            
            while slot_count < posts_per_week:
                day = days[day_idx % len(days)]
                time_str = times[time_idx % len(times)]
                
                time_slots.append({
                    "day": day,
                    "time": time_str,
                    "slot_number": slot_count + 1,
                })
                
                slot_count += 1
                day_idx += 1
                if day_idx % len(days) == 0:
                    time_idx += 1
            
            weekly_schedule[platform] = {
                "time_slots": time_slots,
                "posts_per_week": posts_per_week,
                "reasoning": optimal["reasoning"],
                "timezone": timezone,
            }
        
        return {
            "schedule": weekly_schedule,
            "total_posts_per_week": sum(
                s["posts_per_week"] for s in weekly_schedule.values()
            ),
            "platforms": platforms,
            "timezone": timezone,
        }
