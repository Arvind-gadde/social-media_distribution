"""AI service — platform recommendations and caption generation."""

from __future__ import annotations

from typing import Optional

import structlog

from app.constants import (
    INDIA_REGIONAL_LANGUAGE_CODES,
    PLATFORM_CHAR_LIMITS,
    PLATFORM_DEFAULT_HASHTAGS,
    SUPPORTED_LANGUAGES,
    SUPPORTED_TONES,
)
from app.exceptions import AIServiceError

logger = structlog.get_logger(__name__)

# ── Tone descriptors for prompt engineering ───────────────────────────────

_TONE_DESCRIPTIONS = {
    "casual": "friendly, conversational, and relatable — like texting a friend",
    "professional": "polished, authoritative, and business-appropriate",
    "funny": "humorous, witty, and entertaining with light wordplay",
    "inspirational": "motivational, uplifting, and emotionally resonant",
    "educational": "clear, informative, and easy to understand",
}

_LANGUAGE_INSTRUCTIONS = {
    "en": "Write in English",
    "hi": "Write in Hindi (Devanagari script)",
    "ta": "Write in Tamil",
    "te": "Write in Telugu",
    "bn": "Write in Bengali",
    "mr": "Write in Marathi",
    "gu": "Write in Gujarati",
}


class AIService:
    """Platform recommendations and AI-powered caption generation."""

    def __init__(self, openai_api_key: Optional[str] = None) -> None:
        self._openai_key = openai_api_key

    # ── Platform Recommendations ──────────────────────────────────────────

    def recommend_platforms(
        self,
        media_type: str,
        duration_seconds: float = 0,
        detected_language: str = "en",
    ) -> list[dict]:
        """Return ranked platform recommendations based on content type."""
        is_regional = detected_language in INDIA_REGIONAL_LANGUAGE_CODES

        if media_type == "video":
            return self._recommend_for_video(duration_seconds, is_regional)
        elif media_type == "image":
            return self._recommend_for_image(is_regional)
        else:
            return self._recommend_for_text(is_regional)

    def _recommend_for_video(self, duration_s: float, is_regional: bool) -> list[dict]:
        if duration_s <= 30:
            recs = [
                {"platform": "instagram", "reason": "Reels under 30s get maximum reach", "score": 0.95},
                {"platform": "moj", "reason": "Short videos dominate Moj's feed", "score": 0.92},
                {"platform": "josh", "reason": "Ideal for short Indian creator content", "score": 0.90},
                {"platform": "youtube_shorts", "reason": "Shorts algorithm favours <60s", "score": 0.88},
                {"platform": "chingari", "reason": "Indian short video platform", "score": 0.82},
                {"platform": "roposo", "reason": "Good reach for short clips", "score": 0.78},
                {"platform": "x", "reason": "Short clips go viral on X/Twitter", "score": 0.70},
            ]
        elif duration_s <= 60:
            recs = [
                {"platform": "josh", "reason": "60s creator videos perform best here", "score": 0.92},
                {"platform": "instagram", "reason": "Reels up to 90s", "score": 0.88},
                {"platform": "youtube_shorts", "reason": "Shorts max is 60s", "score": 0.85},
                {"platform": "roposo", "reason": "60s clips work well", "score": 0.80},
                {"platform": "facebook", "reason": "Good reach for 1-min videos", "score": 0.68},
            ]
        else:
            recs = [
                {"platform": "youtube", "reason": "Long-form video performs best on YouTube", "score": 0.97},
                {"platform": "facebook", "reason": "Facebook Watch for long videos", "score": 0.80},
                {"platform": "linkedin", "reason": "Professional long-form video", "score": 0.72},
                {"platform": "instagram", "reason": "IGTV for longer content", "score": 0.65},
            ]

        if is_regional:
            recs.append({"platform": "sharechat", "reason": "Regional language video content thrives here", "score": 0.89})

        return sorted(recs, key=lambda x: x["score"], reverse=True)

    def _recommend_for_image(self, is_regional: bool) -> list[dict]:
        recs = [
            {"platform": "instagram", "reason": "Visual-first platform, highest image engagement", "score": 0.95},
            {"platform": "facebook", "reason": "Images get strong organic reach", "score": 0.82},
            {"platform": "linkedin", "reason": "Great for infographics and professional imagery", "score": 0.78},
            {"platform": "x", "reason": "Images boost engagement 3× on X", "score": 0.72},
        ]
        if is_regional:
            recs.extend([
                {"platform": "sharechat", "reason": "Regional language images perform very well", "score": 0.90},
                {"platform": "koo", "reason": "Good for regional image posts", "score": 0.75},
            ])
        return sorted(recs, key=lambda x: x["score"], reverse=True)

    def _recommend_for_text(self, is_regional: bool) -> list[dict]:
        recs = [
            {"platform": "x", "reason": "Text-first microblogging platform", "score": 0.92},
            {"platform": "linkedin", "reason": "Thought leadership content thrives here", "score": 0.88},
            {"platform": "facebook", "reason": "Text posts with good storytelling", "score": 0.72},
        ]
        if is_regional:
            recs.extend([
                {"platform": "koo", "reason": "Indian microblogging — great for regional text", "score": 0.85},
                {"platform": "sharechat", "reason": "Regional language text content thrives here", "score": 0.93},
            ])
        return sorted(recs, key=lambda x: x["score"], reverse=True)

    # ── Caption Generation ────────────────────────────────────────────────

    def build_platform_caption(self, caption: str, platform: str) -> dict:
        """Trim caption to platform limit and append default hashtags."""
        limit = PLATFORM_CHAR_LIMITS.get(platform, 2000)
        trimmed = caption[:limit]
        hashtags = PLATFORM_DEFAULT_HASHTAGS.get(platform, [])
        return {
            "caption": trimmed,
            "hashtags": hashtags,
            "full_text": f"{trimmed}\n\n{' '.join(hashtags)}".strip() if hashtags else trimmed,
        }

    async def generate_ai_caption(
        self,
        topic: str,
        tone: str,
        language: str,
        media_type: str,
        platforms: list[str],
    ) -> str:
        """Generate a caption using OpenAI GPT-4o-mini."""
        if not self._openai_key:
            raise AIServiceError(
                "OpenAI API key is not configured. Set OPENAI_API_KEY in your .env file."
            )

        if tone not in SUPPORTED_TONES:
            raise AIServiceError(f"Unsupported tone '{tone}'. Choose from: {', '.join(SUPPORTED_TONES)}")

        if language not in SUPPORTED_LANGUAGES:
            raise AIServiceError(f"Unsupported language '{language}'")

        tone_desc = _TONE_DESCRIPTIONS.get(tone, "friendly and conversational")
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, "Write in English")
        platform_list = ", ".join(platforms) if platforms else "social media"

        prompt = f"""You are a social media content expert specialising in Indian audiences and creator culture.

Write a single engaging social media caption for:
- Topic: {topic}
- Content type: {media_type}
- Target platforms: {platform_list}
- Tone: {tone_desc}
- {lang_instruction}

Rules:
1. Under 200 words
2. Include 3–5 relevant emojis naturally placed
3. End with a clear call-to-action
4. If platforms include Instagram/Josh/Moj → make it punchy and visual
5. If LinkedIn is included → professional but human, no buzzwords
6. Do NOT include hashtags (added separately per platform)
7. Output only the caption text — no preamble, no quotes"""

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._openai_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("openai_caption_failed", error=str(exc))
            raise AIServiceError(f"Caption generation failed: {exc}") from exc

    async def suggest_hashtags(
        self, platform: str, caption: str, language: str = "en"
    ) -> list[str]:
        """Suggest trending hashtags using OpenAI, fall back to defaults."""
        if not self._openai_key:
            return PLATFORM_DEFAULT_HASHTAGS.get(platform, [])

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._openai_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate 8 trending hashtags for {platform} in India. "
                        f"Language context: {language}. "
                        f"Caption context: '{caption[:200]}'. "
                        "Return only hashtags separated by spaces, no explanation."
                    ),
                }],
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            return [h for h in text.split() if h.startswith("#")][:8]
        except Exception as exc:
            logger.warning("hashtag_suggestion_failed", error=str(exc))
            return PLATFORM_DEFAULT_HASHTAGS.get(platform, [])
