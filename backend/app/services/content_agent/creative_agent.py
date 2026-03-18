"""
Creative Agent — The "One-to-Many" Content Engine.

This is NOT a replacement for agent.py.  It is an enhanced creative pass
that runs *after* the analyst has enriched each item with virality_score,
gap_explanation, and suggested_angle.  It uses that intelligence to
generate platform-native content that stands out.

Platform strategies:
  - X (Twitter)     : "Hot Take" mode — controversially correct, under 280 chars hook
  - LinkedIn         : "Thought Leadership" — structured insight with data
  - Instagram Reels  : "Hook + Script" — 60-second spoken script with timestamps
  - YouTube Shorts   : Full A/B script variants (Hook A: curiosity gap / Hook B: stat shock)

Claude is the primary LLM.  Gemini/OpenAI are fallbacks.
The existing `generate_content` in agent.py is preserved for backward
compatibility (the /agent/generate API still calls it).  This module is
called by the orchestrator on the pipeline's top items, storing results
in GeneratedPost just like the existing code does.
"""
from __future__ import annotations

import json
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _extract_json_safe(text: str) -> dict | list:
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    text = re.sub(r"```\s*|\s*```", "", text).strip()
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    try:
        return json.loads(text)
    except Exception:
        return {}


async def _call_creative_llm(
    prompt: str,
    system: str,
    anthropic_key: str,
    gemini_key: str,
    openai_key: str,
) -> str:
    import httpx

    if anthropic_key:
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-opus-4-5",
                        "max_tokens": 2000,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"].strip()
        except Exception as exc:
            logger.warning("claude_creative_failed", error=str(exc))

    if gemini_key:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={gemini_key}"
            )
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [
                            {"parts": [{"text": f"{system}\n\n{prompt}"}]}
                        ],
                        "generationConfig": {
                            "temperature": 0.8,
                            "maxOutputTokens": 2000,
                        },
                    },
                )
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
        except Exception as exc:
            logger.warning("gemini_creative_failed", error=str(exc))

    if openai_key:
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.8,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("openai_creative_failed", error=str(exc))

    raise RuntimeError("No LLM available for creative agent")


# ─────────────────────────────────────────────────────────────────────────────
# Platform-specific generators
# ─────────────────────────────────────────────────────────────────────────────

_CREATIVE_SYSTEM = """\
You are an award-winning social media creative director for a tech creator
based in India whose audience is 18-35, curious about AI and technology,
and predominantly English-speaking with some Hindi flair.

Rules:
- Hook must stop the scroll in under 2 seconds.
- Never start with "In a world" or "As AI evolves".
- Emojis are allowed but not forced; use when they add energy.
- Indian context matters: reference Indian companies, Reliance, TCS, ISRO,
  Swiggy, Zomato, or everyday Indian life when relevant — but only when genuinely apt.
- All content must be accurate per the provided facts; do not embellish numbers."""


async def generate_x_hot_take(
    item: dict[str, Any],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    X / Twitter: "Hot Take" mode.
    Thread tweet 1 must be under 240 chars and controversially correct.
    """
    virality = item.get("virality_score", 0.5)
    gap = item.get("suggested_angle", "")
    urgency = "breaking" if virality >= 0.7 else "interesting"

    prompt = f"""Create an X (Twitter) thread for this {urgency} tech story.

STORY: {item['title']}
SUMMARY: {item.get('summary', '')}
KEY POINTS: {'; '.join(item.get('key_points') or [])}
UNIQUE ANGLE TO TAKE: {gap or 'Standard coverage'}
VIRALITY SCORE: {virality:.2f}

The hook tweet must:
- Be under 240 characters
- Use the "Hot Take" format: a strong opinion or surprising truth
- End with 🧵

Return ONLY JSON:
{{
  "hook": "Tweet 1 — the scroll-stopping hook (≤240 chars)",
  "thread_tweets": [
    "Tweet 2 — context (≤260 chars)",
    "Tweet 3 — key insight (≤260 chars)",
    "Tweet 4 — implication or prediction (≤260 chars)",
    "Tweet 5 — CTA + question (≤240 chars)"
  ],
  "hashtags": ["tag1", "tag2", "tag3"],
  "engagement_tips": ["tip1", "tip2"]
}}"""

    result: dict[str, Any] = {
        "hook": "", "thread_tweets": [], "hashtags": [], "engagement_tips": [],
        "caption": "", "call_to_action": "", "script_outline": "",
    }
    try:
        raw = await _call_creative_llm(
            prompt, _CREATIVE_SYSTEM, anthropic_key, gemini_key, openai_key
        )
        parsed = _extract_json_safe(raw)
        if isinstance(parsed, dict):
            result.update(parsed)
            result["caption"] = parsed.get("hook", "")
    except Exception as exc:
        logger.warning("x_hot_take_failed", error=str(exc))
    return result


async def generate_linkedin_thought_leadership(
    item: dict[str, Any],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    LinkedIn: structured "Thought Leadership" post.
    Format: Bold Insight → Data → Why It Matters → Your Take → Question
    """
    gap = item.get("suggested_angle", "")
    sentiment = item.get("sentiment_breakdown", {})
    tone_hint = (
        "professional and analytical"
        if sentiment.get("positive", 0) > sentiment.get("controversial", 0)
        else "measured and balanced, acknowledging controversy"
    )

    prompt = f"""Write a LinkedIn "Thought Leadership" post. Tone: {tone_hint}.

STORY: {item['title']}
SUMMARY: {item.get('summary', '')}
KEY POINTS: {'; '.join(item.get('key_points') or [])}
UNIQUE ANGLE: {gap or 'Standard professional coverage'}
SOURCE: {item.get('source_label', '')}

Structure:
1. HOOK: Bold insight or surprising data point (1–2 lines)
2. CONTEXT: What happened and why (2–3 lines)
3. SO WHAT: Business/professional impact (2–3 lines)
4. MY TAKE: Creator's opinion or prediction (1–2 lines)
5. QUESTION: Open-ended engagement driver

Word count: 250–350 words. 5–8 hashtags.

Return ONLY JSON:
{{
  "hook": "The opening bold statement",
  "caption": "Full post text (hook + body + question, formatted with line breaks)",
  "hashtags": ["Professional", "AI", "..."],
  "call_to_action": "The closing question",
  "engagement_tips": ["tip1", "tip2"]
}}"""

    result: dict[str, Any] = {
        "hook": "", "caption": "", "hashtags": [], "call_to_action": "",
        "thread_tweets": [], "script_outline": "", "engagement_tips": [],
    }
    try:
        raw = await _call_creative_llm(
            prompt, _CREATIVE_SYSTEM, anthropic_key, gemini_key, openai_key
        )
        parsed = _extract_json_safe(raw)
        if isinstance(parsed, dict):
            result.update(parsed)
    except Exception as exc:
        logger.warning("linkedin_thought_leadership_failed", error=str(exc))
    return result


async def generate_instagram_reel_script(
    item: dict[str, Any],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    Instagram Reels: spoken 60-second script with B-Roll cues.
    Hook + Problem + Explain + Impact + CTA.
    """
    broll = item.get("broll_assets", [])
    broll_hint = (
        "B-ROLL AVAILABLE: "
        + "; ".join(a.get("label", "") for a in broll[:3])
        if broll
        else "No specific B-Roll data"
    )
    gap = item.get("suggested_angle", "")

    prompt = f"""Write a 60-second Instagram Reels SPOKEN SCRIPT for a tech creator.

STORY: {item['title']}
SUMMARY: {item.get('summary', '')}
KEY POINTS: {'; '.join(item.get('key_points') or [])}
UNIQUE ANGLE: {gap or 'Standard coverage'}
{broll_hint}

Format as a timestamp script (the creator will read this while recording):
0:00–0:05  HOOK — shocking/funny/bold opener
0:05–0:15  PROBLEM — what's happening and why it matters
0:15–0:40  EXPLANATION — break it down simply, like talking to a friend
0:40–0:50  IMPACT — what this means for the audience's life/career
0:50–1:00  CTA — follow, comment, save

Language: conversational English, okay to drop one Hindi phrase where natural.
Include [B-ROLL: ...] cues in the script where visuals should appear.

Return ONLY JSON:
{{
  "hook": "The first 5 seconds (the line that stops the scroll)",
  "script_outline": "Full timestamp script with B-Roll cues",
  "caption": "Instagram caption (150–200 words) + question at end",
  "hashtags": ["Reels", "AINews", "TechIndia", "..."],
  "call_to_action": "The closing CTA line",
  "engagement_tips": ["tip1", "tip2"]
}}"""

    result: dict[str, Any] = {
        "hook": "", "script_outline": "", "caption": "", "hashtags": [],
        "call_to_action": "", "thread_tweets": [], "engagement_tips": [],
    }
    try:
        raw = await _call_creative_llm(
            prompt, _CREATIVE_SYSTEM, anthropic_key, gemini_key, openai_key
        )
        parsed = _extract_json_safe(raw)
        if isinstance(parsed, dict):
            result.update(parsed)
    except Exception as exc:
        logger.warning("instagram_reel_script_failed", error=str(exc))
    return result


async def generate_youtube_ab_scripts(
    item: dict[str, Any],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    YouTube Shorts: two hook variants for A/B testing.
    Variant A — Curiosity Gap ("You won't believe what X just did")
    Variant B — Stat Shock  ("X just hit Y — here's why that's insane")
    The script body is shared; only the 5-second hook differs.
    """
    gap = item.get("suggested_angle", "")
    broll = item.get("broll_assets", [])
    broll_hint = (
        "; ".join(a.get("label", "") for a in broll[:3]) if broll else ""
    )

    prompt = f"""Write a YouTube Shorts script (60–90 seconds) with TWO hook variants for A/B testing.

STORY: {item['title']}
SUMMARY: {item.get('summary', '')}
KEY POINTS: {'; '.join(item.get('key_points') or [])}
UNIQUE ANGLE: {gap or 'Standard coverage'}
VISUAL ASSETS: {broll_hint or 'Not specified'}

Hook A: CURIOSITY GAP style — implies something shocking without revealing it.
Hook B: STAT SHOCK style — leads with a specific number or fact.

Shared body: 20–70 seconds explaining the story + real-world impact.
Outro (last 10s): Follow CTA + comment question.

Return ONLY JSON:
{{
  "hook": "Hook A text (curiosity gap)",
  "script_outline": "Hook A (0–5s)\\nHook B (ALT 0–5s): [Hook B text]\\n\\nShared body...\\n\\nOutro (final 10s): ...",
  "caption": "YouTube description / caption",
  "hashtags": ["Shorts", "AI", "TechNews", "..."],
  "call_to_action": "Subscribe / comment CTA",
  "engagement_tips": ["Which hook to post first", "Best upload time", "thumbnail tip"]
}}"""

    result: dict[str, Any] = {
        "hook": "", "script_outline": "", "caption": "", "hashtags": [],
        "call_to_action": "", "thread_tweets": [], "engagement_tips": [],
    }
    try:
        raw = await _call_creative_llm(
            prompt, _CREATIVE_SYSTEM, anthropic_key, gemini_key, openai_key
        )
        parsed = _extract_json_safe(raw)
        if isinstance(parsed, dict):
            result.update(parsed)
    except Exception as exc:
        logger.warning("youtube_ab_scripts_failed", error=str(exc))
    return result


# Map platform names to generators
_PLATFORM_GENERATORS = {
    "twitter_thread": generate_x_hot_take,
    "x":              generate_x_hot_take,
    "linkedin":       generate_linkedin_thought_leadership,
    "instagram":      generate_instagram_reel_script,
    "youtube_script": generate_youtube_ab_scripts,
    "youtube_shorts": generate_youtube_ab_scripts,
}


async def generate_creative_content(
    item: dict[str, Any],
    platform: str,
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    Public interface: generate enhanced platform content for one item.

    Falls back to the legacy generator in agent.py if the platform has
    no dedicated creative generator here, preserving backward compatibility.
    """
    generator = _PLATFORM_GENERATORS.get(platform)
    if generator is None:
        # Fall back to existing agent.py generator
        from app.services.content_agent.agent import generate_content as legacy
        return await legacy(
            item, platform, gemini_key=gemini_key, openai_key=openai_key
        )

    return await generator(
        item,
        anthropic_key=anthropic_key,
        gemini_key=gemini_key,
        openai_key=openai_key,
    )


async def run_creative_pass(
    items: list[dict[str, Any]],
    platforms: list[str] | None = None,
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, dict[str, dict]]:
    """
    Generate content for multiple items × multiple platforms.
    Returns {item_id: {platform: content_dict}}.

    Only runs on items with virality_score ≥ 0.50 or is_value_gap=True
    to keep token usage predictable.
    """
    import asyncio

    if platforms is None:
        platforms = ["twitter_thread", "linkedin", "instagram", "youtube_script"]

    eligible = [
        item for item in items
        if item.get("virality_score", 0) >= 0.50 or item.get("is_value_gap", False)
    ][:8]  # cap at 8 items per run

    logger.info(
        "creative_pass_start",
        total_items=len(items),
        eligible=len(eligible),
        platforms=platforms,
    )

    results: dict[str, dict[str, dict]] = {}

    for item in eligible:
        item_results: dict[str, dict] = {}
        for platform in platforms:
            content = await generate_creative_content(
                item,
                platform,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
                openai_key=openai_key,
            )
            item_results[platform] = content
            # Small delay to avoid hammering the LLM API
            await asyncio.sleep(0.3)
        results[item["id"]] = item_results

    logger.info("creative_pass_complete", items_generated=len(results))
    return results
