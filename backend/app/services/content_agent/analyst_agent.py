"""
Analyst Agent — The Intelligence Layer.

Responsibilities:
  1. Virality Score  : S = (R × A) / T²   where R = source authority,
                       A = sentiment acceleration, T = hours since publish.
  2. Trend Velocity  : Cluster items by topic; count how many sources cover
                       the same story within 6 h / 24 h windows.
  3. Value Gap Finder: Compare trending items against last 30 days of
                       generated post topics.  Flag items where the creator
                       has a unique uncovered angle.
  4. B-Roll Assets   : Suggest GitHub repos, arXiv papers, and code-snippet
                       themes that pair well with each item's content.

All four functions are pure async — they receive plain dicts and return
plain dicts.  No DB I/O here; the orchestrator owns persistence.

LLM usage:
  - Virality / Velocity scoring is deterministic math — zero LLM calls.
  - Value Gap and B-Roll use one Claude call each (batched per pipeline run).
  - Falls back to Gemini → OpenAI if Claude key is absent.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ── Source authority weights (R in the virality formula) ──────────────────────
# Higher = more authoritative / higher reach
_SOURCE_AUTHORITY: dict[str, float] = {
    # Tier 1: Lab official blogs & flagship accounts
    "rss_openai_blog":      10.0,
    "rss_anthropic_blog":   10.0,
    "rss_google_ai_blog":   10.0,
    "rss_deepmind_blog":    10.0,
    "rss_huggingface":       9.0,
    "nitter_openai":         9.0,
    "nitter_anthropicai":    9.0,
    "nitter_googledeepMind": 9.0,
    "nitter_huggingface":    9.0,
    # Tier 2: Respected researchers / founders
    "nitter_sama":           8.5,
    "nitter_karpathy":       8.5,
    "nitter_ylecun":         8.0,
    "nitter_andrewyng":      8.0,
    "nitter_demishassabis":  8.5,
    "nitter_fchollet":       7.5,
    # Tier 3: Major tech press
    "rss_techcrunch_ai":     7.0,
    "rss_mit_techreview":    7.5,
    "rss_venturebeat_ai":    6.5,
    "rss_arstechnica":       6.0,
    "rss_theverge":          6.0,
    "rss_wired":             5.5,
    "rss_nyt_tech":          6.0,
    # Tier 4: Community signals
    "hn_top":                6.5,
    "hn_ai":                 6.0,
    "reddit_ml":             7.0,
    "reddit_localllama":     6.0,
    "reddit_openai":         5.5,
    "reddit_artificial":     4.5,
    "reddit_technology":     4.0,
    # Tier 5: GitHub, YouTube, LinkedIn, nitter-misc
    "github_transformers":   7.0,
    "github_langchain":      6.0,
    "github_ollama":         5.5,
    "github_llama_cpp":      5.5,
    "github_autogen":        5.0,
    "github_crewai":         5.0,
}

_DEFAULT_AUTHORITY = 4.0   # any source not in the table


def _authority(source_key: str) -> float:
    return _SOURCE_AUTHORITY.get(source_key, _DEFAULT_AUTHORITY)


def _hours_since(published_at_iso: str | None) -> float:
    """Return age of the item in hours; caps at 72 h to avoid division issues."""
    if not published_at_iso:
        return 12.0  # assume half-day-old if unknown
    try:
        dt = datetime.fromisoformat(published_at_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        hours = max(0.25, delta.total_seconds() / 3600)
        return min(hours, 72.0)
    except (ValueError, TypeError):
        return 12.0


# ─────────────────────────────────────────────────────────────────────────────
# 1. Virality Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_virality_score(
    item: dict[str, Any],
    cross_source_count: int = 1,
    sentiment_acceleration: float = 1.0,
) -> float:
    """
    S = (R × A) / T²

    R = source authority (1–10 scale from table above)
        multiplied by cross-source citation bonus (log₂(n+1))
    A = sentiment_acceleration — caller provides this from cross-source
        topic clustering (1.0 = neutral, >1 = gaining momentum)
    T = hours since publish (min 0.25 to avoid Inf; capped at 72)

    Returned score is clamped to [0.0, 1.0] by normalising against the
    theoretical maximum (R_max=10, A=3, T=0.25 → ~480).

    The theoretical max gives a score > 1 which we normalise with a
    smooth sigmoid-like cap: score / (score + NORMALISER).
    """
    NORMALISER = 40.0    # tunable; controls how quickly score saturates
    # Derivation: R_max(openai_blog=10) × log2(6) × A=2 / T=1² ≈ 51.7
    # NORMALISER < 51.7 ensures a fresh, top-tier, multi-cited item scores >0.5

    R_base = _authority(item.get("source_key", ""))
    R = R_base * math.log2(cross_source_count + 1) if cross_source_count > 1 else R_base
    A = max(0.1, sentiment_acceleration)
    T = _hours_since(item.get("published_at"))

    raw = (R * A) / (T ** 2)
    normalised = raw / (raw + NORMALISER)
    return round(min(1.0, normalised), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Trend Velocity
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_title(title: str) -> str:
    """Strip noise words to surface the topic core for fuzzy matching."""
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    noise = {
        "the", "a", "an", "of", "in", "to", "and", "or", "is", "are", "was",
        "has", "have", "with", "for", "on", "at", "by", "from", "about",
        "that", "this", "it", "its", "how", "why", "what", "new", "latest",
        "update", "release", "releases", "launch", "launched", "announces", "announcing", "introducing",
    }
    tokens = [w for w in title.split() if w not in noise and len(w) > 2]
    return " ".join(sorted(tokens))   # sorted so "gpt openai" == "openai gpt"


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity of two normalised title strings."""
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compute_trend_velocity(items: list[dict[str, Any]]) -> dict[str, float]:
    """
    For each item, count how many OTHER items share ≥40% Jaccard similarity
    on normalised title tokens.  Returns a dict mapping item_id → velocity
    where velocity = count of related items / max_possible (capped at 1.0).

    Also mutates each item dict to add "cross_source_count" for the virality
    formula.
    """
    if not items:
        return {}

    normed = {item["id"]: _normalise_title(item.get("title", "")) for item in items}
    velocity: dict[str, int] = defaultdict(int)

    ids = list(normed.keys())
    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1 :]:
            sim = _jaccard(normed[id_a], normed[id_b])
            if sim >= 0.40:
                velocity[id_a] += 1
                velocity[id_b] += 1

    max_v = max(velocity.values(), default=1)
    for item in items:
        item["cross_source_count"] = 1 + velocity.get(item["id"], 0)

    return {iid: round(velocity.get(iid, 0) / max_v, 4) for iid in ids}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Value Gap Finder
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm_caller(
    anthropic_key: str, gemini_key: str, openai_key: str
):
    """Return an async callable that hits the best available LLM."""

    async def _call(prompt: str, system: str = "") -> str:
        # ── Claude (preferred for analytical work) ────────────────────────
        if anthropic_key:
            try:
                import httpx
                messages: list[dict] = [{"role": "user", "content": prompt}]
                payload: dict[str, Any] = {
                    "model": "claude-opus-4-5",
                    "max_tokens": 2000,
                    "messages": messages,
                }
                if system:
                    payload["system"] = system
                async with httpx.AsyncClient(timeout=45) as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    return resp.json()["content"][0]["text"].strip()
            except Exception as exc:
                logger.warning("claude_analyst_failed", error=str(exc))

        # ── Gemini fallback ───────────────────────────────────────────────
        if gemini_key:
            try:
                import httpx
                full_prompt = f"{system}\n\n{prompt}" if system else prompt
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-1.5-flash:generateContent?key={gemini_key}"
                )
                payload_g = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
                }
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(url, json=payload_g)
                    resp.raise_for_status()
                    return resp.json()["candidates"][0]["content"]["parts"][0][
                        "text"
                    ].strip()
            except Exception as exc:
                logger.warning("gemini_analyst_failed", error=str(exc))

        # ── OpenAI fallback ───────────────────────────────────────────────
        if openai_key:
            try:
                import httpx
                msgs: list[dict] = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt})
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": msgs,
                            "max_tokens": 2000,
                            "temperature": 0.3,
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                logger.warning("openai_analyst_failed", error=str(exc))

        raise RuntimeError("No LLM available for analyst agent")

    return _call


def _extract_json_safe(text: str) -> list | dict:
    """Strip markdown fences and extract first valid JSON structure."""
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    text = re.sub(r"```\s*|\s*```", "", text).strip()
    for start_char, end_char in [("[", "]"), ("{", "}")]:
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
        return []


async def find_value_gaps(
    trending_items: list[dict[str, Any]],
    recent_categories_covered: list[str],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> list[dict[str, Any]]:
    """
    Compare trending items against the creator's recent content history.

    Returns each item dict annotated with:
      - is_value_gap: bool
      - gap_explanation: str  (why this is a gap)
      - suggested_angle: str  (the unique angle to take)

    If no LLM is available, all items are returned with is_value_gap=False
    and a note in gap_explanation.
    """
    if not trending_items:
        return trending_items

    items_summary = "\n".join(
        f"{i + 1}. [{item.get('category', 'other')}] {item['title'][:150]}"
        f" (virality={item.get('virality_score', 0):.2f})"
        for i, item in enumerate(trending_items[:20])
    )

    history_summary = (
        ", ".join(recent_categories_covered[:30])
        if recent_categories_covered
        else "No recent content history available"
    )

    system = (
        "You are a Creative Director for a tech content creator focused on the Indian audience. "
        "Your job is to find stories where the creator has a UNIQUE angle that nobody else has covered. "
        "Be specific, actionable, and honest — not every story is a gap."
    )

    prompt = f"""You are analysing trending tech news for a creator whose recent content covered these topics/categories:
RECENT HISTORY: {history_summary}

TRENDING ITEMS TODAY:
{items_summary}

For each item, decide:
1. Is there a VALUE GAP — an angle, integration, implication, or community concern that trending coverage is missing?
2. If yes: what is the specific unique angle the creator should take?

Return ONLY a JSON array (no prose before or after):
[
  {{
    "index": 1,
    "is_value_gap": true,
    "gap_explanation": "Everyone covers Model X but nobody explains how it breaks Framework Y which this creator's audience uses daily",
    "suggested_angle": "Show a live demo of the conflict, then propose the fix — 60s Reel material"
  }},
  ...
]

Only flag is_value_gap=true when you are genuinely confident. Aim for ≤30% of items being flagged."""

    try:
        caller = _build_llm_caller(anthropic_key, gemini_key, openai_key)
        response = await caller(prompt, system=system)
        gaps = _extract_json_safe(response)
        if isinstance(gaps, list):
            gap_map = {g.get("index"): g for g in gaps if isinstance(g, dict)}
            for i, item in enumerate(trending_items[:20]):
                g = gap_map.get(i + 1, {})
                item["is_value_gap"] = bool(g.get("is_value_gap", False))
                item["gap_explanation"] = g.get("gap_explanation", "")
                item["suggested_angle"] = g.get("suggested_angle", "")
        else:
            logger.warning("value_gap_parse_failed", raw=str(response)[:200])
    except Exception as exc:
        logger.warning("value_gap_failed", error=str(exc))
        for item in trending_items:
            item.setdefault("is_value_gap", False)
            item.setdefault("gap_explanation", "")
            item.setdefault("suggested_angle", "")

    return trending_items


# ─────────────────────────────────────────────────────────────────────────────
# 4. B-Roll Asset Suggester
# ─────────────────────────────────────────────────────────────────────────────

async def suggest_broll_assets(
    items: list[dict[str, Any]],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> list[dict[str, Any]]:
    """
    For each item, suggest concrete visual assets:
      - GitHub repos to screenshot / demo
      - arXiv paper IDs to display
      - Code snippet themes to overlay
      - Competitor products to compare

    Processes items in a single batched LLM call for efficiency.
    Annotates each item with "broll_assets": [{"type":..., "label":..., "url":...}]
    """
    if not items:
        return items

    items_summary = "\n".join(
        f"{i + 1}. [{item.get('category', 'other')}] {item['title'][:150]}"
        for i, item in enumerate(items[:15])
    )

    system = (
        "You are a video production assistant for a tech YouTube/Instagram creator. "
        "Suggest specific, findable visual assets — real GitHub repos, real arXiv IDs, "
        "real product comparison angles. Never hallucinate URLs."
    )

    prompt = f"""For each tech news item below, suggest 2-4 B-Roll / visual assets to use while recording or editing.

ITEMS:
{items_summary}

Asset types you can suggest:
- "github" — a real, popular GitHub repo to show (owner/repo format)
- "arxiv" — a real arXiv paper ID (e.g. 2303.08774)
- "code_snippet" — describe a code concept/pattern to show on screen
- "product_comparison" — two products or approaches to put side by side
- "stat_card" — a specific stat or number to display as a graphic

Return ONLY JSON array:
[
  {{
    "index": 1,
    "assets": [
      {{"type": "github", "label": "openai/whisper — show the repo stars", "url": "https://github.com/openai/whisper"}},
      {{"type": "code_snippet", "label": "Python example: loading the model in 3 lines", "url": ""}},
      {{"type": "stat_card", "label": "GPT-4o vs Gemini 1.5: benchmark comparison table", "url": ""}}
    ]
  }},
  ...
]"""

    try:
        caller = _build_llm_caller(anthropic_key, gemini_key, openai_key)
        response = await caller(prompt, system=system)
        parsed = _extract_json_safe(response)
        if isinstance(parsed, list):
            asset_map = {
                entry.get("index"): entry.get("assets", [])
                for entry in parsed
                if isinstance(entry, dict)
            }
            for i, item in enumerate(items[:15]):
                item["broll_assets"] = asset_map.get(i + 1, [])
        else:
            logger.warning("broll_parse_failed", raw=str(response)[:200])
    except Exception as exc:
        logger.warning("broll_failed", error=str(exc))
        for item in items:
            item.setdefault("broll_assets", [])

    return items


# ─────────────────────────────────────────────────────────────────────────────
# 5. Sentiment Breakdown (lightweight, rule-based + LLM optional)
# ─────────────────────────────────────────────────────────────────────────────

_POSITIVE_SIGNALS = {
    "breakthrough", "launch", "release", "open source", "free", "improves",
    "beats", "surpasses", "state of the art", "sota", "milestone", "record",
    "achieves", "partnership", "funding", "raises",
}
_NEGATIVE_SIGNALS = {
    "outage", "breach", "exploit", "vulnerability", "ban", "layoffs", "sues",
    "controversy", "misleading", "hallucination", "fails", "down", "recall",
    "scandal", "leak", "privacy", "bias", "discrimination", "fired",
}
_CONTROVERSIAL_SIGNALS = {
    "debate", "divided", "argues", "dispute", "disagree", "critics",
    "concern", "regulation", "policy", "congress", "senate", "eu", "lawsuit",
    "anti", "protest", "pushback", "backlash",
}


def compute_sentiment_breakdown(item: dict[str, Any]) -> dict[str, float]:
    """
    Fast rule-based sentiment signal from title + summary text.
    Returns {"positive": p, "negative": n, "controversial": c} that sum to 1.0.
    """
    text = (
        (item.get("title", "") + " " + item.get("summary", "")).lower()
    )
    pos = sum(1 for s in _POSITIVE_SIGNALS if s in text)
    neg = sum(1 for s in _NEGATIVE_SIGNALS if s in text)
    con = sum(1 for s in _CONTROVERSIAL_SIGNALS if s in text)
    total = max(1, pos + neg + con)
    return {
        "positive":     round(pos / total, 3),
        "negative":     round(neg / total, 3),
        "controversial": round(con / total, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Full Analyst Pass  (called by orchestrator)
# ─────────────────────────────────────────────────────────────────────────────

async def run_analyst_pass(
    items: list[dict[str, Any]],
    recent_categories_covered: list[str],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> list[dict[str, Any]]:
    """
    Runs all four analyst functions over `items` in the correct order
    (velocity first, then virality uses the cross_source_count it sets).

    Mutates each item in-place and returns the list.
    """
    # Step 1: trend velocity (pure math — sets cross_source_count on each item)
    compute_trend_velocity(items)

    # Step 2: sentiment breakdown + virality score (pure math)
    for item in items:
        sb = compute_sentiment_breakdown(item)
        item["sentiment_breakdown"] = sb
        # Sentiment acceleration: controversial items spread fastest
        accel = 1.0 + (sb["controversial"] * 1.5) + (sb["positive"] * 0.5)
        item["virality_score"] = compute_virality_score(
            item,
            cross_source_count=item.get("cross_source_count", 1),
            sentiment_acceleration=accel,
        )
        item["trend_velocity"] = item.get("cross_source_count", 1) / max(
            1, len(items)
        )

    # Step 3: value gap (LLM) — only on top-scoring items to save tokens
    top_items = sorted(items, key=lambda x: x.get("virality_score", 0), reverse=True)[
        :15
    ]
    await find_value_gaps(
        top_items,
        recent_categories_covered,
        anthropic_key=anthropic_key,
        gemini_key=gemini_key,
        openai_key=openai_key,
    )

    # Step 4: B-Roll suggestions for value-gap items + highest virality
    broll_candidates = [i for i in top_items if i.get("is_value_gap")] or top_items[:8]
    await suggest_broll_assets(
        broll_candidates,
        anthropic_key=anthropic_key,
        gemini_key=gemini_key,
        openai_key=openai_key,
    )

    return items
