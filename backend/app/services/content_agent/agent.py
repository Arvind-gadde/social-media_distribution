"""
AI Agent — scores, summarises, and generates social content.
Uses Gemini 1.5 Flash (free: 1500 req/day) first, falls back to OpenAI gpt-3.5-turbo.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
import structlog

from app.services.content_agent.normalization import normalize_generated_content

logger = structlog.get_logger(__name__)


async def _call_llm(prompt: str, system: str = "", gemini_key: str = "", openai_key: str = "") -> str:
    if gemini_key:
        try:
            import httpx
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={gemini_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": f"{system}\n\n{prompt}" if system else prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as exc:
            logger.warning("gemini_failed", error=str(exc))

    if openai_key:
        try:
            import httpx
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={"model": "gpt-3.5-turbo", "messages": messages, "max_tokens": 1500, "temperature": 0.7},
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("openai_failed", error=str(exc))

    # No LLM available — return empty to let callers degrade gracefully
    logger.warning("no_llm_available", hint="Set GEMINI_API_KEY or OPENAI_API_KEY in .env")
    return ""


def _extract_json(text: str) -> dict | list:
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    text = re.sub(r"```\s*|\s*```", "", text).strip()
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i+1])
                        except json.JSONDecodeError:
                            break
    try:
        return json.loads(text)
    except Exception:
        return {}


async def score_items(items: list[dict], gemini_key: str = "", openai_key: str = "") -> list[dict]:
    if not items:
        return []
    items_text = "\n".join([
        f"{i+1}. TITLE: {item['title'][:150]}\n   SOURCE: {item['source_label']}"
        for i, item in enumerate(items)
    ])
    prompt = f"""Score these tech news items for an AI/tech content creator in India.
Rate relevance for educational social media posts about AI and technology.

Scoring:
- 0.9-1.0: Major AI model release, breakthrough research, industry-changing news
- 0.7-0.8: Significant product launch, important paper, popular framework update
- 0.5-0.6: Interesting tech news, tool release, opinion from key person
- 0.3-0.4: Minor update, tangentially related
- 0.0-0.2: Not relevant

Categories: model_release, research_paper, product_launch, funding, opinion_take, tutorial, industry_news, open_source, policy_safety, other

Items:
{items_text}

Respond ONLY with JSON array:
[{{"index": 1, "score": 0.85, "category": "model_release"}}, ...]"""

    try:
        response = await _call_llm(prompt, gemini_key=gemini_key, openai_key=openai_key)
        scores = _extract_json(response)
        if isinstance(scores, list) and len(scores) > 0:
            score_map = {s.get("index"): s for s in scores}
            for i, item in enumerate(items):
                score_data = score_map.get(i + 1, {})
                item["relevance_score"] = float(score_data.get("score", 0.5))
                item["category"] = score_data.get("category", "other")
        else:
            # LLM returned empty or unparseable — assign sensible defaults
            for item in items:
                item["relevance_score"] = 0.5
                item["category"] = "other"
    except Exception as exc:
        logger.warning("scoring_failed", error=str(exc))
        for item in items:
            item["relevance_score"] = 0.5
            item["category"] = "other"
    return items


async def summarise_item(item: dict, gemini_key: str = "", openai_key: str = "") -> dict:
    content_preview = (item.get("raw_content") or "")[:2000]
    prompt = f"""Summarise this tech news for a content creator explaining technology to everyday people.

TITLE: {item['title']}
SOURCE: {item['source_label']}
CONTENT: {content_preview}

Return ONLY this JSON:
{{
  "summary": "2-3 sentence plain English explanation of what happened and why it matters",
  "key_points": ["point 1", "point 2", "point 3"],
  "why_it_matters": "One sentence on real-world impact for regular people"
}}"""
    try:
        response = await _call_llm(prompt, gemini_key=gemini_key, openai_key=openai_key)
        parsed = _extract_json(response)
        if isinstance(parsed, dict) and parsed.get("summary"):
            item["summary"] = parsed.get("summary", "")
            item["key_points"] = parsed.get("key_points", [])
        else:
            # LLM returned empty — create fallback from raw_content
            _apply_fallback_summary(item)
    except Exception as exc:
        logger.warning("summarise_failed", title=item.get("title"), error=str(exc))
        _apply_fallback_summary(item)
    return item


def _apply_fallback_summary(item: dict) -> None:
    """Create a basic summary from raw_content when LLM is unavailable."""
    raw = (item.get("raw_content") or "").strip()
    if raw:
        # Clean and truncate to 300 chars for a readable brief
        snippet = raw[:300].rsplit(" ", 1)[0] if len(raw) > 300 else raw
        item["summary"] = snippet + ("…" if len(raw) > 300 else "")
    elif item.get("title"):
        item["summary"] = item["title"]
    item.setdefault("key_points", [])


PLATFORM_INSTRUCTIONS = {
    "instagram": """Instagram post for tech content creator targeting Indian audience.
- Hook: First line must stop the scroll (numbers, questions, or shocking facts)
- Caption: 150-200 words, conversational, emojis okay
- End with a question to boost comments
- 15-20 hashtags mixing niche AI + broad reach""",

    "linkedin": """LinkedIn post for professional tech audience.
- Professional but approachable tone, 250-350 words
- Start with bold insight or surprising stat
- Structure: Hook → Context → Why it matters → Your take → Question
- 5-8 industry-specific hashtags""",

    "twitter_thread": """Twitter/X thread for tech enthusiasts.
- Tweet 1 (hook): Under 240 chars, makes people want to read more. Use 🧵
- Tweets 2-5: Each explains one key point. Under 260 chars each.
- Final tweet: Takeaway + CTA. Under 240 chars.
- 3-5 hashtags""",

    "youtube_script": """YouTube Shorts/Reels script outline (60-90 seconds).
- Hook (0-5s): Shocking statement or question
- Problem/Context (5-20s): What is this and why care?
- Explanation (20-50s): How it works, simple analogies
- Real-world impact (50-70s): How will this affect them?
- CTA (70-90s): Follow for more, comment your thoughts
- Keep language simple, explain like talking to a 16-year-old""",
}


async def generate_content(item: dict, platform: str, gemini_key: str = "", openai_key: str = "") -> dict:
    platform_guide = PLATFORM_INSTRUCTIONS.get(platform, PLATFORM_INSTRUCTIONS["instagram"])
    summary = item.get("summary", item.get("title", ""))
    key_points = "\n".join(f"- {p}" for p in (item.get("key_points") or []))

    prompt = f"""You are a top tech content creator in India. Create engaging social media content.

NEWS ITEM:
Title: {item['title']}
Summary: {summary}
Key points:
{key_points}
Source: {item['source_label']}
Original URL: {item.get('source_url', '')}

PLATFORM: {platform.upper()}
INSTRUCTIONS: {platform_guide}

Return ONLY this JSON:
{{
  "hook": "The opening scroll-stopping line",
  "caption": "Main body of the post",
  "hashtags": ["hashtag1", "hashtag2"],
  "call_to_action": "The closing CTA",
  "thread_tweets": ["tweet1", "tweet2"],
  "script_outline": "For video: timestamp outline",
  "engagement_tips": ["tip1", "tip2"]
}}"""

    result = {
        "hook": "", "caption": "", "hashtags": [], "call_to_action": "",
        "thread_tweets": [], "script_outline": "", "engagement_tips": [],
    }
    try:
        response = await _call_llm(prompt, gemini_key=gemini_key, openai_key=openai_key)
        parsed = _extract_json(response)
        if isinstance(parsed, dict):
            result.update(parsed)
    except Exception as exc:
        logger.warning("generate_content_failed", platform=platform, error=str(exc))
        result["caption"] = f"📱 {item['title']}\n\n{summary}"
        result["hashtags"] = ["#AI", "#Technology", "#Innovation", "#TechNews", "#ArtificialIntelligence"]
    return normalize_generated_content(result)


async def run_agent_pipeline(gemini_key: str = "", openai_key: str = "") -> dict:
    from app.db.session import AsyncSessionLocal
    from app.models.models import ContentItem, ContentCategory
    from sqlalchemy import select, update
    import uuid

    BATCH_SIZE = 10
    MIN_SCORE = 0.5
    MAX_TO_PROCESS = 30

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContentItem)
            .where(ContentItem.is_processed == False)
            .order_by(ContentItem.fetched_at.desc())
            .limit(MAX_TO_PROCESS)
        )
        items = result.scalars().all()

    if not items:
        return {"processed": 0, "top_items": 0}

    item_dicts = [
        {
            "id": str(item.id), "title": item.title,
            "raw_content": item.raw_content or "",
            "source_label": item.source_label,
            "source_url": item.source_url or "",
            "relevance_score": 0.0, "category": "other", "summary": "", "key_points": [],
        }
        for item in items
    ]

    scored = []
    for i in range(0, len(item_dicts), BATCH_SIZE):
        batch = item_dicts[i:i + BATCH_SIZE]
        scored_batch = await score_items(batch, gemini_key=gemini_key, openai_key=openai_key)
        scored.extend(scored_batch)

    top_items = sorted([i for i in scored if i["relevance_score"] >= MIN_SCORE],
                       key=lambda x: x["relevance_score"], reverse=True)[:10]
    for item in top_items:
        await summarise_item(item, gemini_key=gemini_key, openai_key=openai_key)

    async with AsyncSessionLocal() as db:
        for item_dict in scored:
            try:
                cat_value = item_dict.get("category", "other")
                try:
                    cat = ContentCategory(cat_value)
                except ValueError:
                    cat = ContentCategory.OTHER
                await db.execute(
                    update(ContentItem)
                    .where(ContentItem.id == uuid.UUID(item_dict["id"]))
                    .values(
                        relevance_score=item_dict.get("relevance_score", 0.0),
                        category=cat,
                        summary=item_dict.get("summary") or None,
                        key_points=item_dict.get("key_points") or None,
                        is_processed=True,
                        is_trending=item_dict.get("relevance_score", 0.0) >= 0.8,
                    )
                )
            except Exception as exc:
                logger.warning("db_update_failed", error=str(exc))
        await db.commit()

    logger.info("agent_pipeline_complete", processed=len(scored), top_items=len(top_items))
    return {"processed": len(scored), "top_items": len(top_items)}
