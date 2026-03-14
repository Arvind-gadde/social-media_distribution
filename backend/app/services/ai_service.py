"""AI service — platform recommendations and caption generation.

Provider strategy:
  1. Gemini (google-generativeai) — free tier: 1,500 req/day
  2. OpenAI GPT-4o-mini — fallback if Gemini fails or key missing
  3. Rule-based — final fallback, always works with no API key
"""

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
    """Platform recommendations and AI-powered caption generation.

    Dependency-injected with API keys so it is testable without environment setup.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ) -> None:
        self._gemini_key = gemini_api_key or ""
        self._openai_key = openai_api_key or ""

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
                {"platform": "instagram", "reason": "Reels up to 90s supported", "score": 0.88},
                {"platform": "youtube_shorts", "reason": "Shorts max is 60s", "score": 0.85},
                {"platform": "facebook", "reason": "Good for short video content", "score": 0.75},
                {"platform": "x", "reason": "Video clips perform well", "score": 0.70},
            ]
        else:
            recs = [
                {"platform": "youtube", "reason": "Best platform for long-form video", "score": 0.96},
                {"platform": "facebook", "reason": "Long videos reach older demographics", "score": 0.80},
                {"platform": "linkedin", "reason": "Professional long-form video", "score": 0.72},
            ]

        if is_regional:
            regional = [
                {"platform": "sharechat", "reason": "Top regional language social platform", "score": 0.93},
                {"platform": "koo", "reason": "Indian multilingual microblogging", "score": 0.85},
            ]
            recs = regional + recs

        return recs[:8]

    def _recommend_for_image(self, is_regional: bool) -> list[dict]:
        recs = [
            {"platform": "instagram", "reason": "Best platform for visual content", "score": 0.96},
            {"platform": "facebook", "reason": "Image posts drive strong engagement", "score": 0.85},
            {"platform": "linkedin", "reason": "Images boost professional post reach", "score": 0.80},
            {"platform": "x", "reason": "Images increase tweet visibility by 3x", "score": 0.78},
        ]
        if is_regional:
            recs = [{"platform": "sharechat", "reason": "Image-heavy regional audience", "score": 0.88}] + recs
        return recs

    def _recommend_for_text(self, is_regional: bool) -> list[dict]:
        recs = [
            {"platform": "x", "reason": "Built for short-form text posts", "score": 0.92},
            {"platform": "linkedin", "reason": "Professional text content thrives here", "score": 0.88},
            {"platform": "facebook", "reason": "Good reach for text posts", "score": 0.75},
        ]
        if is_regional:
            recs = [
                {"platform": "koo", "reason": "Regional language microblogging", "score": 0.90},
                {"platform": "sharechat", "reason": "Text posts in regional languages", "score": 0.85},
            ] + recs
        return recs

    # ── Caption Generation ────────────────────────────────────────────────

    async def generate_caption(
        self,
        topic: str,
        tone: str = "casual",
        language: str = "en",
        media_type: str = "video",
        platforms: list[str] | None = None,
    ) -> str:
        """
        Generate a social media caption.
        Tries Gemini → OpenAI → rule-based fallback in order.
        Never raises — always returns something useful.
        """
        validated_tone = tone if tone in _TONE_DESCRIPTIONS else "casual"
        validated_lang = language if language in _LANGUAGE_INSTRUCTIONS else "en"
        prompt = self._build_prompt(topic, validated_tone, validated_lang, media_type, platforms or [])

        if self._gemini_key:
            try:
                return await self._call_gemini(prompt)
            except Exception as exc:
                logger.warning("gemini_caption_failed", error=str(exc))

        if self._openai_key:
            try:
                return await self._call_openai(prompt)
            except Exception as exc:
                logger.warning("openai_caption_failed", error=str(exc))

        logger.info("ai_caption_fallback_to_rule_based")
        return self._rule_based_caption(topic, validated_tone)

    async def suggest_hashtags(
        self, platform: str, caption: str, language: str = "en"
    ) -> list[str]:
        """Return hashtag suggestions. Falls back to platform defaults."""
        defaults = list(PLATFORM_DEFAULT_HASHTAGS.get(platform, []))
        if not (self._gemini_key or self._openai_key):
            return defaults[:15]

        prompt = (
            f"Generate 10 relevant hashtags for this social media caption on {platform}. "
            f"Caption: {caption[:200]}\n"
            "Return only hashtags, one per line, starting with #. No explanations."
        )

        raw = ""
        if self._gemini_key:
            try:
                raw = await self._call_gemini(prompt, max_tokens=200)
            except Exception as exc:
                logger.warning("gemini_hashtag_failed", error=str(exc))

        if not raw and self._openai_key:
            try:
                raw = await self._call_openai(prompt, max_tokens=200)
            except Exception as exc:
                logger.warning("openai_hashtag_failed", error=str(exc))

        if raw:
            tags = [
                line.strip()
                for line in raw.splitlines()
                if line.strip().startswith("#")
            ]
            if tags:
                return tags[:15]

        return defaults[:15]

    # ── Prompt builder ────────────────────────────────────────────────────

    def _build_prompt(
        self,
        topic: str,
        tone: str,
        language: str,
        media_type: str,
        platforms: list[str],
    ) -> str:
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, "Write in English")
        tone_desc = _TONE_DESCRIPTIONS.get(tone, _TONE_DESCRIPTIONS["casual"])
        platform_str = ", ".join(platforms) if platforms else "social media"

        char_limits = []
        for p in platforms:
            limit = PLATFORM_CHAR_LIMITS.get(p)
            if limit:
                char_limits.append(f"{p}: {limit} chars")
        limits_str = "; ".join(char_limits) if char_limits else ""

        return (
            f"Write a {tone_desc} social media caption for a {media_type} about: {topic}\n"
            f"Target platforms: {platform_str}\n"
            f"{f'Character limits — {limits_str}' if limits_str else ''}\n"
            f"{lang_instruction}.\n"
            "Include 3-5 relevant emojis. Do NOT include hashtags (generated separately).\n"
            "Return only the caption text, no explanations."
        )

    def _rule_based_caption(self, topic: str, tone: str) -> str:
        """Deterministic fallback when no AI keys are available."""
        openings = {
            "casual": f"Hey everyone! Check out my latest {topic} content 🎉",
            "professional": f"Excited to share insights on {topic} with my network.",
            "funny": f"Plot twist: {topic} is actually amazing 😂",
            "inspirational": f"Every journey starts with one step. Today's focus: {topic} 🌟",
            "educational": f"Let's learn something new about {topic} today 📚",
        }
        return openings.get(tone, openings["casual"])

    # ── Provider calls ────────────────────────────────────────────────────

    async def _call_gemini(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Google Gemini API (gemini-1.5-flash — free tier)."""
        import google.generativeai as genai  # type: ignore[import]

        genai.configure(api_key=self._gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # google-generativeai is sync; run in thread pool to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            ),
        )
        text = response.text.strip()
        if not text:
            raise AIServiceError("Gemini returned empty response")
        return text

    async def _call_openai(self, prompt: str, max_tokens: int = 500) -> str:
        """Call OpenAI GPT-4o-mini API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._openai_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise AIServiceError("OpenAI returned empty response")
        return text