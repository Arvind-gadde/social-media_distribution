"""Niche prompt library — per-niche, per-agent system prompts.

From grok.md §2 & claude.md §6:
  All agent prompts are templated per niche. When the orchestrator runs,
  it queries this library for the niche-specific system prompt for the
  current agent step. Falls back to the generic PromptCatalog version
  if no niche override exists.

Seeded on startup via seed_niche_prompts().
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ─── Niche Prompt Templates ─────────────────────────────────────────────────
# key: (niche_slug, agent_type) → prompt context
# These override the generic PromptCatalog prompts with niche-specific tone,
# sources, vocabulary, and audience expectations.

NICHE_PROMPT_OVERRIDES: dict[tuple[str, str], dict[str, Any]] = {
    # ── Fitness ──────────────────────────────────────────────────────────
    ("fitness", "scorer"): {
        "niche_context": (
            "You are scoring content for fitness creators. Prioritize:\n"
            "- New exercise science research or training methodologies\n"
            "- Nutrition breakthroughs (protein timing, supplements)\n"
            "- Viral workout challenges on TikTok/Instagram Reels\n"
            "- Before/after transformation content potential\n"
            "- Indian fitness culture: yoga fusion, cricket fitness, desi diet plans\n"
            "Deprioritize generic wellness platitudes and unverified supplement claims."
        ),
    },
    ("fitness", "creative"): {
        "niche_context": (
            "You are creating content for fitness creators targeting 18-35 year olds.\n"
            "Tone: Motivational but grounded. No bro-science.\n"
            "Hooks: Start with a bold claim or visual transformation.\n"
            "Platform notes:\n"
            "- Reels/TikTok: 15-30s, trending audio, fast cuts\n"
            "- YouTube Shorts: Can go 45-60s, overlay text for silent viewers\n"
            "- Twitter/X: Thread format works for workout breakdowns\n"
            "- LinkedIn: 'What fitness taught me about business' angle\n"
            "Always include: workout name, sets/reps, and a motivational CTA."
        ),
    },
    # ── Tech ─────────────────────────────────────────────────────────────
    ("tech", "scorer"): {
        "niche_context": (
            "You are scoring content for tech creators. Prioritize:\n"
            "- Breaking announcements from FAANG, OpenAI, Google, Apple\n"
            "- Open source project launches and viral GitHub repos\n"
            "- AI/ML breakthroughs with practical applications\n"
            "- Developer tools, frameworks, and productivity hacks\n"
            "- Indian tech ecosystem: startup funding, UPI innovations, ISRO\n"
            "Deprioritize vaporware announcements and recycled press releases."
        ),
    },
    ("tech", "creative"): {
        "niche_context": (
            "You are creating content for tech creators and developers.\n"
            "Tone: Smart, concise, opinionated. Avoid corporate speak.\n"
            "Hooks: Lead with 'Hot take:' or 'This changes everything:'\n"
            "Platform notes:\n"
            "- Twitter/X: Thread with code snippets, numbered lists\n"
            "- LinkedIn: Professional angle, career/industry implications\n"
            "- YouTube: Tutorial or 'explained in 60s' format\n"
            "- Instagram: Infographic carousels with dark mode aesthetics\n"
            "Include: specific tool names, version numbers, benchmarks when available."
        ),
    },
    # ── Finance ──────────────────────────────────────────────────────────
    ("finance", "scorer"): {
        "niche_context": (
            "You are scoring content for finance/investing creators. Prioritize:\n"
            "- Market-moving events (RBI decisions, Fed policy, IPOs)\n"
            "- Personal finance education (SIP, mutual funds, tax saving)\n"
            "- Fintech innovations (UPI, crypto regulation in India)\n"
            "- Investment thesis breakdowns\n"
            "CRITICAL: Flag anything that could be construed as financial advice.\n"
            "Deprioritize pump-and-dump signals and unverified 'insider tips'."
        ),
    },
    ("finance", "creative"): {
        "niche_context": (
            "You are creating content for finance creators in the Indian market.\n"
            "Tone: Educational, trustworthy. Use data, charts, numbers.\n"
            "MANDATORY DISCLAIMER: Always include 'This is not financial advice.'\n"
            "Platform notes:\n"
            "- YouTube: Long-form analysis, screen recordings with charts\n"
            "- Instagram: Carousel infographics (tax tips, SIP calculators)\n"
            "- Twitter/X: Numbered list with key takeaways\n"
            "- LinkedIn: Professional analysis with market context\n"
            "Use ₹ currency, Indian examples (Nifty, Sensex, RBI)."
        ),
    },
    # ── Comedy/Entertainment ─────────────────────────────────────────────
    ("comedy", "scorer"): {
        "niche_context": (
            "You are scoring content for comedy/entertainment creators. Prioritize:\n"
            "- Trending memes and viral audio\n"
            "- Pop culture moments (Bollywood, cricket, IPL, politics)\n"
            "- Relatable Indian scenarios (rickshaw rides, chai culture, exam season)\n"
            "- Controversial-but-safe takes that drive comments\n"
            "Deprioritize offensive humor, slur-based content, and political extremes."
        ),
    },
    ("comedy", "creative"): {
        "niche_context": (
            "You are creating content for comedy/entertainment creators.\n"
            "Tone: Relatable, witty, self-deprecating. Think TVF/AIB style.\n"
            "Hooks: Situation-based — 'When your mom says...' / 'POV:'\n"
            "Platform notes:\n"
            "- Reels/TikTok: Lip-sync, trending audio, POV skits (15-30s)\n"
            "- YouTube Shorts: Extended punchline format (30-60s)\n"
            "- Twitter/X: One-liner + meme image\n"
            "Use Hinglish naturally. Reference current Indian pop culture."
        ),
    },
    # ── Education ────────────────────────────────────────────────────────
    ("education", "scorer"): {
        "niche_context": (
            "You are scoring content for education creators. Prioritize:\n"
            "- Exam prep tips (JEE, NEET, UPSC, CAT, GATE)\n"
            "- EdTech innovations and free learning resources\n"
            "- Study techniques backed by cognitive science\n"
            "- Career guidance (placements, skill-based learning)\n"
            "- Government education policy changes\n"
            "Deprioritize generic 'study hard' motivation without actionable advice."
        ),
    },
    ("education", "creative"): {
        "niche_context": (
            "You are creating content for education creators in India.\n"
            "Tone: Encouraging, clear, practical. Use analogies.\n"
            "Hooks: 'The mistake 90% of students make...' / '5-minute hack:'\n"
            "Platform notes:\n"
            "- YouTube: Whiteboard explainers, screen recordings\n"
            "- Instagram: Carousel (step-by-step study guides)\n"
            "- Twitter/X: Thread with key formulas or tips\n"
            "Reference Indian exams, boards, and university systems specifically."
        ),
    },
    # ── Food/Cooking ─────────────────────────────────────────────────────
    ("cooking", "scorer"): {
        "niche_context": (
            "You are scoring content for food/cooking creators. Prioritize:\n"
            "- Viral recipe trends (e.g., cloud bread, protein ice cream)\n"
            "- Quick recipe formats (under 5 ingredients, under 15 min)\n"
            "- Regional Indian cuisine spotlights\n"
            "- Healthy alternatives to popular dishes\n"
            "- Festival/seasonal recipe opportunities\n"
            "Deprioritize overly complex restaurant-style recipes without home alternatives."
        ),
    },
    ("cooking", "creative"): {
        "niche_context": (
            "You are creating content for food/cooking creators.\n"
            "Tone: Warm, sensory, 'home kitchen' feel. Use food emojis.\n"
            "Hooks: Overhead shot of final dish / 'You won't believe this is healthy'\n"
            "Platform notes:\n"
            "- Reels/TikTok: Overhead recipe video with text overlay (30-60s)\n"
            "- YouTube: Full recipe + tips + story format\n"
            "- Instagram: Carousel (recipe card format with steps)\n"
            "Include: ingredient list, cook time, difficulty level, serving size."
        ),
    },
    # ── Gaming ───────────────────────────────────────────────────────────
    ("gaming", "scorer"): {
        "niche_context": (
            "You are scoring content for gaming creators. Prioritize:\n"
            "- New game releases and major updates\n"
            "- BGMI/Free Fire/Valorant meta changes (Indian gaming scene)\n"
            "- Esports tournament results and highlights\n"
            "- Gaming hardware deals and reviews\n"
            "- Tips/tricks that actually improve gameplay\n"
            "Deprioritize clickbait 'leaked' content and unverified rumors."
        ),
    },
    ("gaming", "creative"): {
        "niche_context": (
            "You are creating content for gaming creators.\n"
            "Tone: Energetic, competitive, community-driven.\n"
            "Hooks: Gameplay clip with 'Watch what happens next' / tier lists\n"
            "Platform notes:\n"
            "- YouTube: Gameplay + commentary, top 10 lists\n"
            "- Reels/TikTok: Clutch moments, quick tips (15-30s)\n"
            "- Twitter/X: Hot takes on meta, tier list images\n"
            "Reference popular Indian gamers and Indian esports scene."
        ),
    },
}


async def get_niche_prompt_context(
    db: AsyncSession,
    niche_slug: str,
    agent_type: str,
) -> str | None:
    """Get niche-specific prompt context for an agent type.

    Returns the niche_context string if a niche override exists,
    otherwise None (caller should use generic PromptCatalog version).

    Args:
        db: Database session (unused for now, reserved for DB-backed overrides).
        niche_slug: The niche identifier (e.g., 'fitness', 'tech').
        agent_type: The agent step (e.g., 'scorer', 'creative').

    Returns:
        Niche-specific context string, or None if no override exists.
    """
    override = NICHE_PROMPT_OVERRIDES.get((niche_slug, agent_type))
    if override:
        return override.get("niche_context")
    return None


async def get_prompt_for_agent(
    db: AsyncSession,
    agent_type: str,
    niche_slug: str | None = None,
) -> dict[str, Any]:
    """Resolve the best prompt configuration for an agent + niche combination.

    Resolution order:
      1. Niche-specific override (if niche_slug provided and override exists)
      2. PromptCatalog active version
      3. Fallback to empty dict (caller must handle)

    Returns a dict with: system_prompt, niche_context, temperature, max_tokens,
    recommended_provider, recommended_model.
    """
    from app.domains.intelligence.models import PromptCatalog, PromptVersion

    # Resolve from PromptCatalog
    catalog_name = f"content.{agent_type}" if not agent_type.startswith("content.") else agent_type
    result = await db.execute(
        select(PromptCatalog).where(
            PromptCatalog.name == catalog_name,
            PromptCatalog.is_active == True,
        )
    )
    catalog = result.scalar_one_or_none()

    prompt_config: dict[str, Any] = {}

    if catalog and catalog.active_version_id:
        version_result = await db.execute(
            select(PromptVersion).where(PromptVersion.id == catalog.active_version_id)
        )
        version = version_result.scalar_one_or_none()
        if version:
            prompt_config = {
                "system_prompt": version.system_prompt,
                "temperature": version.temperature,
                "max_tokens": version.max_tokens,
                "recommended_provider": version.recommended_provider,
                "recommended_model": version.recommended_model,
                "catalog_id": str(catalog.id),
                "version_id": str(version.id),
                "version": version.version,
            }

    # Layer niche context on top
    if niche_slug:
        niche_ctx = await get_niche_prompt_context(db, niche_slug, agent_type)
        if niche_ctx:
            prompt_config["niche_context"] = niche_ctx

    return prompt_config
