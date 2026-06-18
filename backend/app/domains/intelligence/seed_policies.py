"""Provider Policy + Prompt Catalog seed data.

Seeds the default routing policies per openai.md §8.7 and initial prompt
catalog entries for the agent pipeline stages.
"""
from __future__ import annotations

import hashlib


# ─── Provider Policies ──────────────────────────────────────────────────────
# From openai.md §8.7:
#   Ingestion / large-context triage     → Gemini primary
#   Structured generation / tool use     → OpenAI primary
#   Critique / refinement / review       → Anthropic primary

PROVIDER_POLICY_SEEDS: list[dict] = [
    {
        "task_type": "ingestion",
        "primary_provider": "gemini",
        "primary_model": "gemini-2.0-flash",
        "fallback_provider_1": "openai",
        "fallback_model_1": "gpt-4o-mini",
        "fallback_provider_2": None,
        "fallback_model_2": None,
        "max_retries": 2,
        "timeout_seconds": 120,
        "cost_per_1k_input": 0.00007,
        "cost_per_1k_output": 0.0003,
        "priority": 10,
    },
    {
        "task_type": "scoring",
        "primary_provider": "gemini",
        "primary_model": "gemini-2.0-flash",
        "fallback_provider_1": "openai",
        "fallback_model_1": "gpt-4o-mini",
        "fallback_provider_2": None,
        "fallback_model_2": None,
        "max_retries": 2,
        "timeout_seconds": 60,
        "cost_per_1k_input": 0.00007,
        "cost_per_1k_output": 0.0003,
        "priority": 20,
    },
    {
        "task_type": "analysis",
        "primary_provider": "gemini",
        "primary_model": "gemini-2.0-flash",
        "fallback_provider_1": "openai",
        "fallback_model_1": "gpt-4o-mini",
        "fallback_provider_2": None,
        "fallback_model_2": None,
        "max_retries": 2,
        "timeout_seconds": 90,
        "cost_per_1k_input": 0.00007,
        "cost_per_1k_output": 0.0003,
        "priority": 30,
    },
    {
        "task_type": "generation",
        "primary_provider": "openai",
        "primary_model": "gpt-4o-mini",
        "fallback_provider_1": "gemini",
        "fallback_model_1": "gemini-2.0-flash",
        "fallback_provider_2": "anthropic",
        "fallback_model_2": "claude-3-5-haiku-20241022",
        "max_retries": 2,
        "timeout_seconds": 90,
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "priority": 40,
    },
    {
        "task_type": "critique",
        "primary_provider": "anthropic",
        "primary_model": "claude-3-5-haiku-20241022",
        "fallback_provider_1": "openai",
        "fallback_model_1": "gpt-4o-mini",
        "fallback_provider_2": None,
        "fallback_model_2": None,
        "max_retries": 2,
        "timeout_seconds": 90,
        "cost_per_1k_input": 0.0008,
        "cost_per_1k_output": 0.004,
        "priority": 50,
    },
    {
        "task_type": "fact_check",
        "primary_provider": "openai",
        "primary_model": "gpt-4o-mini",
        "fallback_provider_1": "gemini",
        "fallback_model_1": "gemini-2.0-flash",
        "fallback_provider_2": None,
        "fallback_model_2": None,
        "max_retries": 3,
        "timeout_seconds": 60,
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
        "priority": 60,
    },
]


# ─── Prompt Catalog Entries ─────────────────────────────────────────────────
# Core prompts used by the agent pipeline with initial versions.

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


_SCORER_SYSTEM_PROMPT = """You are a content relevance scorer for creator niches.
Given a source document and a niche context, rate 0.0–1.0 on:
- Relevance to niche (40%)
- Timeliness (20%)
- Virality potential (20%)
- Content creation opportunity (20%)
Respond with JSON: {"score": float, "reasoning": str}"""

_ANALYST_SYSTEM_PROMPT = """You are a content analyst for creator intelligence.
Given a scored source document, produce:
1. A concise 2-3 sentence summary
2. 3-5 key points as bullet strings
3. A category classification
4. Content gap analysis (is there an underserved angle?)
5. Suggested content angles for creators
Respond with structured JSON."""

_FACT_CHECKER_SYSTEM_PROMPT = """You are a fact-checking analyst.
Given a source document and its claims:
1. Identify verifiable claims
2. Rate confidence (0.0-1.0) that claims are accurate
3. Flag any potentially misleading statements
4. Note if source is from a known reliable outlet
Respond with JSON: {"passed": bool, "confidence": float, "flagged_claims": [str]}"""

_CREATIVE_SYSTEM_PROMPT = """You are a content creation specialist for social media creators.
Given a source document, niche context, and target platforms, generate:
- Attention-grabbing hook (first 3 seconds)
- Platform-specific caption
- Script outline (if video)
- Relevant hashtags (10-15)
- Call-to-action suggestion
- Engagement tips

IMPORTANT: Match the creator's niche voice and audience.
Respond with structured JSON per platform."""


PROMPT_CATALOG_SEEDS: list[dict] = [
    {
        "name": "content.score",
        "description": "Score source documents for niche relevance and content potential",
        "agent_type": "scorer",
        "version": "v1.0",
        "system_prompt": _SCORER_SYSTEM_PROMPT,
        "recommended_provider": "gemini",
        "recommended_model": "gemini-2.0-flash",
        "temperature": 0.3,
        "max_tokens": 500,
    },
    {
        "name": "content.analyze",
        "description": "Analyze source documents for key insights and content gaps",
        "agent_type": "analyst",
        "version": "v1.0",
        "system_prompt": _ANALYST_SYSTEM_PROMPT,
        "recommended_provider": "gemini",
        "recommended_model": "gemini-2.0-flash",
        "temperature": 0.5,
        "max_tokens": 1500,
    },
    {
        "name": "content.fact_check",
        "description": "Verify claims and flag potentially misleading content",
        "agent_type": "fact_checker",
        "version": "v1.0",
        "system_prompt": _FACT_CHECKER_SYSTEM_PROMPT,
        "recommended_provider": "openai",
        "recommended_model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 800,
    },
    {
        "name": "content.generate",
        "description": "Generate platform-specific content variants from insights",
        "agent_type": "creative",
        "version": "v1.0",
        "system_prompt": _CREATIVE_SYSTEM_PROMPT,
        "recommended_provider": "openai",
        "recommended_model": "gpt-4o-mini",
        "temperature": 0.8,
        "max_tokens": 3000,
    },
]


async def seed_provider_policies(db) -> int:
    """Seed default provider routing policies.

    Returns the count of policies inserted. Skips existing task_types.
    """
    from sqlalchemy import select
    from app.domains.intelligence.models import ProviderPolicy

    inserted = 0
    for policy_data in PROVIDER_POLICY_SEEDS:
        existing = await db.execute(
            select(ProviderPolicy).where(
                ProviderPolicy.task_type == policy_data["task_type"]
            )
        )
        if existing.scalar_one_or_none():
            continue

        policy = ProviderPolicy(**policy_data)
        db.add(policy)
        inserted += 1

    if inserted > 0:
        await db.commit()
    return inserted


async def seed_prompt_catalog(db) -> int:
    """Seed initial prompt catalog entries.

    Returns the count of catalog entries + versions inserted.
    """
    from sqlalchemy import select
    from app.domains.intelligence.models import PromptCatalog, PromptVersion

    inserted = 0
    for entry in PROMPT_CATALOG_SEEDS:
        existing = await db.execute(
            select(PromptCatalog).where(PromptCatalog.name == entry["name"])
        )
        if existing.scalar_one_or_none():
            continue

        catalog = PromptCatalog(
            name=entry["name"],
            description=entry.get("description"),
            agent_type=entry["agent_type"],
        )
        db.add(catalog)
        await db.flush()

        # Create initial version
        version = PromptVersion(
            catalog_id=catalog.id,
            version=entry["version"],
            system_prompt=entry["system_prompt"],
            recommended_provider=entry.get("recommended_provider"),
            recommended_model=entry.get("recommended_model"),
            temperature=entry.get("temperature", 0.7),
            max_tokens=entry.get("max_tokens", 2000),
            sha256_hash=_sha(entry["system_prompt"]),
        )
        db.add(version)
        await db.flush()

        # Set active version
        catalog.active_version_id = version.id
        inserted += 1

    if inserted > 0:
        await db.commit()
    return inserted
