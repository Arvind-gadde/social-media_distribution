"""
Fact-Checker Agent — Technical Accuracy Guardian.

Before a content item is surfaced to the creator, this agent:
  1. Extracts technical claims from the item's title, summary, and key_points.
  2. Evaluates each claim against its own knowledge (and web context where
     available) to flag unverified or disputed facts.
  3. Returns a structured fact_check_result so the UI can warn the creator.

Design decisions:
  - Only runs on items with relevance_score ≥ 0.65 (high-value items where
    accuracy really matters).
  - A "check" is intentionally conservative: the agent flags uncertainty
    rather than asserting something is false.  False positives here are
    far less harmful than unchecked misinformation.
  - If no LLM is available the item passes unchecked (fact_check_passed=None).
  - Results are stored in ContentInsight; this module has no DB I/O.
"""
from __future__ import annotations

import json
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Minimum relevance_score for a fact-check to be performed
FACT_CHECK_THRESHOLD = 0.65

# Max items per pipeline run (to keep token cost predictable)
MAX_ITEMS_PER_RUN = 10


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


async def _call_llm(
    prompt: str,
    system: str,
    anthropic_key: str,
    gemini_key: str,
    openai_key: str,
) -> str:
    import httpx

    if anthropic_key:
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-opus-4-5",
                        "max_tokens": 1500,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"].strip()
        except Exception as exc:
            logger.warning("claude_factcheck_failed", error=str(exc))

    if gemini_key:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={gemini_key}"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [
                            {"parts": [{"text": f"{system}\n\n{prompt}"}]}
                        ],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 1500,
                        },
                    },
                )
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
        except Exception as exc:
            logger.warning("gemini_factcheck_failed", error=str(exc))

    if openai_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 1500,
                        "temperature": 0.1,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("openai_factcheck_failed", error=str(exc))

    raise RuntimeError("No LLM available for fact-checker")


def _build_claims_text(item: dict[str, Any]) -> str:
    """Assemble the text from which we will extract claims."""
    parts = [item.get("title", "")]
    if item.get("summary"):
        parts.append(item["summary"])
    if item.get("key_points"):
        parts.extend(item["key_points"])
    return "\n".join(p for p in parts if p)


SYSTEM_PROMPT = """\
You are a meticulous technical fact-checker for a tech content creator.
Your job is to identify specific technical claims in a news item and
assess whether each claim is:
  - "verified"   : well-established, widely corroborated fact
  - "plausible"  : consistent with known information but hard to independently verify right now
  - "unverified" : lacks corroboration or could not be assessed
  - "disputed"   : contradicts known facts or is contested in the community

Be conservative. When in doubt, mark as "unverified" rather than "verified".
Prefer brevity in notes — one sentence maximum per claim.
Never fabricate benchmark numbers or paper citations."""


async def fact_check_item(
    item: dict[str, Any],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """
    Fact-check a single item.

    Returns dict:
    {
      "fact_check_passed": bool | None,
      "fact_check_confidence": float | None,   # 0–1
      "flagged_claims": [{"claim": str, "verdict": str, "note": str}, ...]
    }

    `fact_check_passed` is True when all claims are verified/plausible,
    False when any are unverified/disputed, None on error.
    """
    empty_result: dict[str, Any] = {
        "fact_check_passed": None,
        "fact_check_confidence": None,
        "flagged_claims": [],
    }

    claims_text = _build_claims_text(item)
    if not claims_text.strip():
        return empty_result

    prompt = f"""Analyse the following tech news item and identify up to 6 specific technical claims.
For each claim, give a verdict and a brief note.

ITEM:
{claims_text[:2500]}

Return ONLY JSON:
{{
  "claims": [
    {{
      "claim": "The exact claim extracted from the text",
      "verdict": "verified|plausible|unverified|disputed",
      "note": "One sentence explanation"
    }}
  ],
  "overall_confidence": 0.85
}}"""

    try:
        raw = await _call_llm(
            prompt, SYSTEM_PROMPT,
            anthropic_key=anthropic_key,
            gemini_key=gemini_key,
            openai_key=openai_key,
        )
        parsed = _extract_json_safe(raw)
        if not isinstance(parsed, dict):
            return empty_result

        claims: list[dict] = parsed.get("claims", [])
        confidence: float = float(parsed.get("overall_confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        unacceptable = {"unverified", "disputed"}
        all_pass = all(
            c.get("verdict", "unverified") not in unacceptable for c in claims
        )

        return {
            "fact_check_passed": all_pass,
            "fact_check_confidence": round(confidence, 3),
            "flagged_claims": claims,
        }

    except Exception as exc:
        logger.warning("fact_check_item_failed", item_id=item.get("id"), error=str(exc))
        return empty_result


async def run_fact_checker_pass(
    items: list[dict[str, Any]],
    *,
    anthropic_key: str = "",
    gemini_key: str = "",
    openai_key: str = "",
) -> list[dict[str, Any]]:
    """
    Run fact-checking on the subset of items that meet the threshold.

    Processes sequentially to avoid rate-limit bursts.  Annotates each
    item in-place with fact_check_* keys and returns the full list.
    """
    import asyncio

    eligible = [
        item for item in items
        if item.get("relevance_score", 0) >= FACT_CHECK_THRESHOLD
    ][:MAX_ITEMS_PER_RUN]

    logger.info(
        "fact_checker_start",
        total=len(items),
        eligible=len(eligible),
    )

    for item in eligible:
        result = await fact_check_item(
            item,
            anthropic_key=anthropic_key,
            gemini_key=gemini_key,
            openai_key=openai_key,
        )
        item["fact_check_passed"] = result["fact_check_passed"]
        item["fact_check_confidence"] = result["fact_check_confidence"]
        item["flagged_claims"] = result["flagged_claims"]
        # Small delay between calls to avoid rate-limit spikes
        await asyncio.sleep(0.5)

    # Items that weren't checked get None values (not False — they weren't checked)
    checked_ids = {item["id"] for item in eligible}
    for item in items:
        if item["id"] not in checked_ids:
            item.setdefault("fact_check_passed", None)
            item.setdefault("fact_check_confidence", None)
            item.setdefault("flagged_claims", [])

    logger.info("fact_checker_complete", checked=len(eligible))
    return items
