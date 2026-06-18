"""Video analysis service for content intelligence."""
from typing import Dict, List, Optional
import re
import structlog

log = structlog.get_logger(__name__)


class VideoAnalyzer:
    """Analyze video content for optimization."""
    
    # Strong hook patterns
    STRONG_HOOKS = [
        r"^(watch|see|look|check)",
        r"^(you won't believe|you need to|you have to)",
        r"^(this is|here's|this)",
        r"^(i'm going to|let me|i'll show you)",
        r"^(the secret|the truth|the reason)",
        r"^(how to|why|what|when)",
        r"^(stop|don't|never)",
        r"^\d+ (ways|tips|tricks|secrets|reasons)",
    ]
    
    # Pacing indicators
    SLOW_INDICATORS = [
        "um", "uh", "like", "you know", "basically", "actually",
    ]
    
    def analyze_video(
        self,
        video_url: str,
        transcript: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict:
        """Analyze video content.
        
        Args:
            video_url: URL to video file
            transcript: Optional transcript text
            duration_seconds: Video duration
            thumbnail_url: Optional thumbnail URL
            
        Returns:
            Analysis results with scores and recommendations
        """
        analysis = {
            "video_url": video_url,
            "duration_seconds": duration_seconds,
            "has_transcript": transcript is not None,
            "has_thumbnail": thumbnail_url is not None,
        }
        
        # Analyze transcript if available
        if transcript:
            transcript_analysis = self._analyze_transcript(transcript, duration_seconds)
            analysis.update(transcript_analysis)
        
        # Analyze duration
        if duration_seconds:
            duration_analysis = self._analyze_duration(duration_seconds)
            analysis.update(duration_analysis)
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        # Calculate overall quality score
        analysis["quality_score"] = self._calculate_quality_score(analysis)
        
        return analysis
    
    def _analyze_transcript(self, transcript: str, duration: Optional[int]) -> Dict:
        """Analyze video transcript."""
        words = transcript.split()
        word_count = len(words)
        
        # Extract first 3 seconds (roughly first 10 words)
        hook_text = " ".join(words[:10]) if len(words) >= 10 else transcript
        
        # Analyze hook strength
        hook_score = self._score_hook(hook_text)
        
        # Detect filler words (pacing issues)
        filler_count = sum(
            transcript.lower().count(filler)
            for filler in self.SLOW_INDICATORS
        )
        filler_ratio = filler_count / word_count if word_count > 0 else 0
        
        # Calculate speaking pace (words per minute)
        wpm = None
        if duration and duration > 0:
            wpm = (word_count / duration) * 60
        
        return {
            "word_count": word_count,
            "hook_text": hook_text,
            "hook_score": hook_score,
            "filler_count": filler_count,
            "filler_ratio": round(filler_ratio, 3),
            "speaking_pace_wpm": round(wpm, 1) if wpm else None,
        }
    
    def _score_hook(self, hook_text: str) -> float:
        """Score hook strength (0-1)."""
        hook_lower = hook_text.lower()
        
        # Check for strong hook patterns
        pattern_matches = sum(
            1 for pattern in self.STRONG_HOOKS
            if re.search(pattern, hook_lower)
        )
        
        # Check for numbers (engaging)
        has_numbers = bool(re.search(r'\d+', hook_text))
        
        # Check for questions (engaging)
        has_question = '?' in hook_text
        
        # Calculate score
        score = 0.3  # Base score
        
        if pattern_matches > 0:
            score += 0.3
        
        if has_numbers:
            score += 0.2
        
        if has_question:
            score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_duration(self, duration: int) -> Dict:
        """Analyze video duration."""
        # Optimal durations by platform
        optimal_ranges = {
            "tiktok": (15, 60),
            "instagram_reel": (15, 90),
            "youtube_short": (15, 60),
            "youtube_video": (480, 1200),  # 8-20 minutes
        }
        
        # Determine best platform fit
        platform_fit = {}
        for platform, (min_dur, max_dur) in optimal_ranges.items():
            if min_dur <= duration <= max_dur:
                platform_fit[platform] = 1.0
            elif duration < min_dur:
                platform_fit[platform] = duration / min_dur
            else:
                platform_fit[platform] = max_dur / duration
        
        return {
            "platform_fit": {k: round(v, 3) for k, v in platform_fit.items()},
            "best_platforms": sorted(
                platform_fit.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
        }
    
    def _calculate_quality_score(self, analysis: Dict) -> float:
        """Calculate overall video quality score."""
        score = 0.5  # Base score
        
        # Hook quality
        if "hook_score" in analysis:
            score += analysis["hook_score"] * 0.3
        
        # Pacing (low filler ratio is good)
        if "filler_ratio" in analysis:
            filler_penalty = analysis["filler_ratio"] * 0.2
            score -= filler_penalty
        
        # Speaking pace (120-160 WPM is optimal)
        if analysis.get("speaking_pace_wpm"):
            wpm = analysis["speaking_pace_wpm"]
            if 120 <= wpm <= 160:
                score += 0.2
            elif 100 <= wpm <= 180:
                score += 0.1
        
        return round(max(min(score, 1.0), 0.0), 3)
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Hook recommendations
        if analysis.get("hook_score", 0) < 0.7:
            recommendations.append(
                "🎣 Strengthen your hook: Start with a question, number, or bold statement in the first 3 seconds"
            )
        
        # Filler word recommendations
        if analysis.get("filler_ratio", 0) > 0.05:
            recommendations.append(
                "⚡ Reduce filler words: Cut 'um', 'uh', 'like' to improve pacing and professionalism"
            )
        
        # Speaking pace recommendations
        wpm = analysis.get("speaking_pace_wpm")
        if wpm and wpm < 100:
            recommendations.append(
                "🏃 Speed up: Your pace is slow. Aim for 120-160 words per minute for better engagement"
            )
        elif wpm and wpm > 180:
            recommendations.append(
                "🐢 Slow down: Your pace is too fast. Aim for 120-160 words per minute for clarity"
            )
        
        # Duration recommendations
        if analysis.get("duration_seconds"):
            duration = analysis["duration_seconds"]
            if duration < 15:
                recommendations.append(
                    "⏱️ Too short: Videos under 15 seconds may not perform well. Aim for 15-60 seconds"
                )
            elif duration > 180 and "youtube_video" not in str(analysis.get("best_platforms", [])):
                recommendations.append(
                    "✂️ Consider trimming: Long videos work best on YouTube. For other platforms, aim for under 90 seconds"
                )
        
        # Platform recommendations
        if analysis.get("best_platforms"):
            best = analysis["best_platforms"][0][0]
            recommendations.append(
                f"📱 Best platform fit: {best.replace('_', ' ').title()}"
            )
        
        return recommendations
    
    def suggest_clips(
        self,
        transcript: str,
        duration_seconds: int,
        target_duration: int = 30,
    ) -> List[Dict]:
        """Suggest best clips for short-form content.
        
        Args:
            transcript: Full transcript
            duration_seconds: Total video duration
            target_duration: Target clip duration in seconds
            
        Returns:
            List of suggested clips with timestamps
        """
        # Simple implementation: divide into segments
        words = transcript.split()
        total_words = len(words)
        
        if total_words == 0 or duration_seconds == 0:
            return []
        
        # Calculate words per second
        wps = total_words / duration_seconds
        
        # Calculate words per target duration
        words_per_clip = int(wps * target_duration)
        
        clips = []
        for i in range(0, total_words, words_per_clip):
            clip_words = words[i:i + words_per_clip]
            clip_text = " ".join(clip_words)
            
            # Calculate timestamps
            start_time = int(i / wps)
            end_time = int((i + len(clip_words)) / wps)
            
            # Score this clip
            clip_score = self._score_hook(clip_text[:50])  # Score first part
            
            clips.append({
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "text": clip_text[:100] + "..." if len(clip_text) > 100 else clip_text,
                "score": clip_score,
            })
        
        # Sort by score and return top 5
        clips.sort(key=lambda x: x["score"], reverse=True)
        return clips[:5]
    
    def generate_caption_suggestions(
        self,
        transcript: str,
        platform: str = "instagram",
    ) -> List[str]:
        """Generate caption suggestions from transcript.
        
        Args:
            transcript: Video transcript
            platform: Target platform
            
        Returns:
            List of caption suggestions
        """
        # Extract key phrases (simple implementation)
        sentences = transcript.split('.')
        
        captions = []
        
        # Option 1: First sentence as hook
        if sentences:
            first = sentences[0].strip()
            if len(first) > 10:
                captions.append(first + "... 👀")
        
        # Option 2: Question format
        if '?' in transcript:
            questions = [s.strip() + '?' for s in transcript.split('?') if s.strip()]
            if questions:
                captions.append(questions[0])
        
        # Option 3: Key takeaway
        if len(sentences) > 1:
            captions.append(f"Key takeaway: {sentences[1].strip()}... 💡")
        
        return captions[:3]
