"""LLM provider router — selects (provider, model) per task with cost-aware fallbacks.

Public API (used by app.runtime.orchestration.nodes and tests):
  - class TaskType(str, Enum)
  - class ProviderRouter:
        policy: dict
        get_provider(task: TaskType, use_fallback: bool = False) -> (str, str)
        get_reason(task: TaskType) -> str
        estimate_cost(task: TaskType, input_tokens: int, output_tokens: int) -> float
  - router: ProviderRouter singleton
"""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class TaskType(str, Enum):
    INGESTION_TRIAGE = "ingestion_triage"
    STRUCTURED_GENERATION = "structured_generation"
    CRITIQUE_REFINEMENT = "critique_refinement"
    LONG_CONTEXT_ANALYSIS = "long_context_analysis"
    CREATIVE_WRITING = "creative_writing"
    TREND_ANALYSIS = "trend_analysis"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    SUMMARIZATION = "summarization"


# Approximate per-1k token prices (USD). Used only for budget estimates.
_PRICE_PER_1K: dict[Tuple[str, str], Tuple[float, float]] = {
    ("gemini", "gemini-1.5-flash"): (0.000075, 0.0003),
    ("gemini", "gemini-2.0-flash"): (0.000075, 0.0003),
    ("openai", "gpt-4o"): (0.005, 0.015),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
}


# Primary for 429-prone Gemini paths is openai; gemini kept only for the
# cheapest ingestion path (and to honor the test contract).
_POLICY: dict[TaskType, dict] = {
    TaskType.INGESTION_TRIAGE: {
        "primary": ("gemini", "gemini-1.5-flash"),
        "fallback": ("openai", "gpt-4o-mini"),
        "reason": "Cheap, long context window for triage",
    },
    TaskType.STRUCTURED_GENERATION: {
        "primary": ("openai", "gpt-4o"),
        "fallback": ("anthropic", "claude-3-5-sonnet-20241022"),
        "reason": "Best tool-use and structured-output reliability",
    },
    TaskType.CRITIQUE_REFINEMENT: {
        "primary": ("anthropic", "claude-3-5-sonnet-20241022"),
        "fallback": ("openai", "gpt-4o"),
        "reason": "Best editorial quality",
    },
    TaskType.LONG_CONTEXT_ANALYSIS: {
        "primary": ("openai", "gpt-4o"),
        "fallback": ("anthropic", "claude-3-5-sonnet-20241022"),
        "reason": "Stable for multi-document analysis",
    },
    TaskType.CREATIVE_WRITING: {
        "primary": ("anthropic", "claude-3-5-sonnet-20241022"),
        "fallback": ("openai", "gpt-4o"),
        "reason": "Best creative quality",
    },
    TaskType.TREND_ANALYSIS: {
        "primary": ("openai", "gpt-4o-mini"),
        "fallback": ("openai", "gpt-4o"),
        "reason": "Fast, cheap classification of trend signals",
    },
    TaskType.COMPETITOR_ANALYSIS: {
        "primary": ("openai", "gpt-4o-mini"),
        "fallback": ("anthropic", "claude-3-5-sonnet-20241022"),
        "reason": "Cheap structured pattern extraction",
    },
    TaskType.SUMMARIZATION: {
        "primary": ("openai", "gpt-4o-mini"),
        "fallback": ("anthropic", "claude-3-5-sonnet-20241022"),
        "reason": "Cheap summarization with good fidelity",
    },
}


class ProviderRouter:
    def __init__(self) -> None:
        self.policy = _POLICY

    def get_provider(
        self, task: TaskType, use_fallback: bool = False
    ) -> Tuple[str, str]:
        entry = self.policy[task]
        return entry["fallback" if use_fallback else "primary"]

    def get_reason(self, task: TaskType) -> str:
        return self.policy[task]["reason"]

    def estimate_cost(
        self, task: TaskType, input_tokens: int, output_tokens: int
    ) -> float:
        provider, model = self.get_provider(task)
        price_in, price_out = _PRICE_PER_1K.get((provider, model), (0.001, 0.003))
        return (input_tokens / 1000.0) * price_in + (output_tokens / 1000.0) * price_out


router = ProviderRouter()
