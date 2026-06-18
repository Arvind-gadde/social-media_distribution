"""Niche-aware agent adapter — bridges legacy agents to unified LLM + prompt library.

This module wraps the content pipeline stages (score, analyze, fact-check, create)
with niche context from the prompt library and routes through the unified LLMProvider
instead of raw API keys.

Usage in orchestrator:
    adapter = NicheAgentAdapter(llm_provider, db, niche_slug="fitness")
    scored = await adapter.score_items(items)
    analyzed = await adapter.analyze_item(item)
    checked = await adapter.fact_check_item(item)
    content = await adapter.generate_content(item, platform="instagram")
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

import structlog

from app.integrations.llm.provider import LLMProvider, LLMResponse, TaskType

logger = structlog.get_logger(__name__)


def _extract_json(text: str) -> dict | list:
    """Extract JSON from LLM response, handling markdown fences."""
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    text = re.sub(r"```\s*|\s*```", "", text).strip()
    obj_idx = text.find('{')
    arr_idx = text.find('[')
    if obj_idx == -1 and arr_idx == -1:
        return {}
    if arr_idx != -1 and (obj_idx == -1 or arr_idx < obj_idx):
        start_char, end_char, start = '[', ']', arr_idx
    else:
        start_char, end_char, start = '{', '}', obj_idx
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
    try:
        return json.loads(text)
    except Exception:
        return {}


class NicheAgentAdapter:
    """Niche-aware agent that uses unified LLM provider + prompt library.

    Resolves prompts per-niche, tracks costs via LLMProvider,
    and standardizes input/output for the orchestrator pipeline.
    """

    def __init__(
        self,
        llm: LLMProvider,
        db,
        *,
        niche_slug: str | None = None,
        workspace_id: uuid.UUID | None = None,
    ) -> None:
        self._llm = llm
        self._db = db
        self._niche_slug = niche_slug
        self._workspace_id = workspace_id
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_cost_usd = 0.0

    @property
    def usage_summary(self) -> dict[str, Any]:
        """Return aggregate usage stats for this adapter session."""
        return {
            "tokens_in": self._total_tokens_in,
            "tokens_out": self._total_tokens_out,
            "cost_usd": round(self._total_cost_usd, 6),
        }

    async def _get_prompt_config(self, agent_type: str) -> dict[str, Any]:
        """Resolve prompt config from niche library + catalog."""
        from app.domains.intelligence.prompt_library import get_prompt_for_agent
        return await get_prompt_for_agent(
            self._db, agent_type, self._niche_slug,
        )

    async def _call(
        self,
        task_type: TaskType,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = True,
    ) -> LLMResponse:
        """Make an LLM call through the unified provider."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await self._llm.complete(
            task_type=task_type,
            messages=messages,
            workspace_id=self._workspace_id,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            db_session=self._db,
        )
        self._total_tokens_in += response.tokens_in
        self._total_tokens_out += response.tokens_out
        self._total_cost_usd += response.cost_usd
        return response

    # ── Score ────────────────────────────────────────────────────────────

    async def score_items(self, items: list[dict]) -> list[dict]:
        """Score a batch of source documents for niche relevance.

        Returns items with added relevance_score and category fields.
        """
        if not items:
            return []

        prompt_config = await self._get_prompt_config("scorer")
        system_prompt = prompt_config.get("system_prompt", "")
        niche_context = prompt_config.get("niche_context", "")

        full_system = system_prompt
        if niche_context:
            full_system = f"{system_prompt}\n\n## Niche Context\n{niche_context}"

        items_text = "\n".join([
            f"{i + 1}. TITLE: {item['title'][:150]}\n   SOURCE: {item.get('source_label', 'unknown')}"
            for i, item in enumerate(items)
        ])

        user_prompt = (
            f"Score these {len(items)} content items.\n\n"
            f"Items:\n{items_text}\n\n"
            f"Respond ONLY with JSON array:\n"
            f'[{{"index": 1, "score": 0.85, "category": "model_release", '
            f'"reasoning": "brief reason"}}, ...]'
        )

        try:
            response = await self._call(
                TaskType.SCORING, full_system, user_prompt,
                temperature=prompt_config.get("temperature", 0.3),
                max_tokens=prompt_config.get("max_tokens", 500),
            )
            scores = _extract_json(response.content)
            if isinstance(scores, list) and scores:
                score_map = {s.get("index"): s for s in scores}
                for i, item in enumerate(items):
                    score_data = score_map.get(i + 1, {})
                    item["relevance_score"] = float(score_data.get("score", 0.5))
                    item["category"] = score_data.get("category", "other")
                    item["score_reasoning"] = score_data.get("reasoning", "")
            else:
                for item in items:
                    item["relevance_score"] = 0.5
                    item["category"] = "other"
        except Exception as exc:
            logger.warning("niche_scoring_failed", error=str(exc))
            for item in items:
                item["relevance_score"] = 0.5
                item["category"] = "other"

        return items

    # ── Analyze ──────────────────────────────────────────────────────────

    async def analyze_item(self, item: dict) -> dict:
        """Deep analysis: summary, key points, content gap detection."""
        prompt_config = await self._get_prompt_config("analyst")
        system_prompt = prompt_config.get("system_prompt", "You are a content analyst.")
        niche_context = prompt_config.get("niche_context", "")

        full_system = system_prompt
        if niche_context:
            full_system = f"{system_prompt}\n\n## Niche Context\n{niche_context}"

        content_preview = (item.get("raw_content") or "")[:3000]
        user_prompt = (
            f"Analyze this source document:\n\n"
            f"TITLE: {item['title']}\n"
            f"SOURCE: {item.get('source_label', 'unknown')}\n"
            f"CONTENT:\n{content_preview}\n\n"
            f"Respond with JSON:\n"
            f'{{"summary": "2-3 sentences", "key_points": ["point1", "point2"], '
            f'"category": "topic_category", "is_value_gap": false, '
            f'"gap_explanation": "why this is underserved", '
            f'"suggested_angle": "content angle for creators"}}'
        )

        try:
            response = await self._call(
                TaskType.ANALYSIS, full_system, user_prompt,
                temperature=prompt_config.get("temperature", 0.5),
                max_tokens=prompt_config.get("max_tokens", 1500),
            )
            parsed = _extract_json(response.content)
            if isinstance(parsed, dict) and parsed.get("summary"):
                item["summary"] = parsed["summary"]
                item["key_points"] = parsed.get("key_points", [])
                item["is_value_gap"] = parsed.get("is_value_gap", False)
                item["gap_explanation"] = parsed.get("gap_explanation", "")
                item["suggested_angle"] = parsed.get("suggested_angle", "")
            else:
                self._apply_fallback_summary(item)
        except Exception as exc:
            logger.warning("niche_analysis_failed", error=str(exc))
            self._apply_fallback_summary(item)

        return item

    # ── Fact Check ───────────────────────────────────────────────────────

    async def fact_check_item(self, item: dict) -> dict:
        """Verify claims and flag potentially misleading content."""
        prompt_config = await self._get_prompt_config("fact_checker")
        system_prompt = prompt_config.get(
            "system_prompt", "You are a fact-checking analyst.",
        )

        content = (item.get("raw_content") or item.get("summary", ""))[:2000]
        user_prompt = (
            f"Fact-check this content:\n\n"
            f"TITLE: {item['title']}\n"
            f"CONTENT:\n{content}\n\n"
            f"Respond with JSON:\n"
            f'{{"passed": true, "confidence": 0.9, '
            f'"flagged_claims": ["claim that needs verification"]}}'
        )

        try:
            response = await self._call(
                TaskType.FACT_CHECK, system_prompt, user_prompt,
                temperature=prompt_config.get("temperature", 0.2),
                max_tokens=prompt_config.get("max_tokens", 800),
            )
            parsed = _extract_json(response.content)
            if isinstance(parsed, dict):
                item["fact_check_passed"] = parsed.get("passed", True)
                item["fact_check_confidence"] = float(parsed.get("confidence", 0.5))
                item["flagged_claims"] = parsed.get("flagged_claims", [])
            else:
                item["fact_check_passed"] = True
                item["fact_check_confidence"] = 0.5
        except Exception as exc:
            logger.warning("niche_fact_check_failed", error=str(exc))
            item["fact_check_passed"] = True
            item["fact_check_confidence"] = 0.5

        return item

    # ── Generate Content ─────────────────────────────────────────────────

    async def generate_content(
        self, item: dict, platform: str,
    ) -> dict[str, Any]:
        """Generate platform-specific content variant with niche context."""
        prompt_config = await self._get_prompt_config("creative")
        system_prompt = prompt_config.get("system_prompt", "You are a content creator.")
        niche_context = prompt_config.get("niche_context", "")

        full_system = system_prompt
        if niche_context:
            full_system = f"{system_prompt}\n\n## Niche Context\n{niche_context}"

        summary = item.get("summary", item.get("title", ""))
        key_points = "\n".join(
            f"- {p}" for p in (item.get("key_points") or [])
        )
        angle = item.get("suggested_angle", "")

        user_prompt = (
            f"Create content for {platform.upper()}.\n\n"
            f"SOURCE:\n"
            f"Title: {item['title']}\n"
            f"Summary: {summary}\n"
            f"Key points:\n{key_points}\n"
            f"Suggested angle: {angle}\n"
            f"Source URL: {item.get('source_url', '')}\n\n"
            f"Respond with JSON:\n"
            f'{{"hook": "scroll-stopping opening", '
            f'"caption": "main body", '
            f'"hashtags": ["hashtag1", "hashtag2"], '
            f'"call_to_action": "closing CTA", '
            f'"thread_tweets": ["tweet1", "tweet2"], '
            f'"script_outline": "for video platforms", '
            f'"engagement_tips": ["tip1", "tip2"]}}'
        )

        result: dict[str, Any] = {
            "hook": "", "caption": "", "hashtags": [],
            "call_to_action": "", "thread_tweets": [],
            "script_outline": "", "engagement_tips": [],
        }

        try:
            response = await self._call(
                TaskType.GENERATION, full_system, user_prompt,
                temperature=prompt_config.get("temperature", 0.8),
                max_tokens=prompt_config.get("max_tokens", 3000),
            )
            parsed = _extract_json(response.content)
            if isinstance(parsed, dict):
                result.update(parsed)
        except Exception as exc:
            logger.warning(
                "niche_generation_failed",
                platform=platform, error=str(exc),
            )
            result["caption"] = f"📱 {item['title']}\n\n{summary}"
            result["hashtags"] = ["#ContentCreator", "#AIContent"]

        return result

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _apply_fallback_summary(item: dict) -> None:
        """Create a basic summary from raw_content when LLM is unavailable."""
        raw = (item.get("raw_content") or "").strip()
        if raw:
            snippet = raw[:300].rsplit(" ", 1)[0] if len(raw) > 300 else raw
            item["summary"] = snippet + ("…" if len(raw) > 300 else "")
        elif item.get("title"):
            item["summary"] = item["title"]
        item.setdefault("key_points", [])
