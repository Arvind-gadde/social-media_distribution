"""Unified LLM Provider — cost-aware routing across OpenAI, Gemini, Anthropic.

Routing policy (based on research synthesis):
  - Primary: OpenAI (gpt-4o-mini for structured gen, gpt-4o for complex)
  - Fallback 1: Gemini Flash (cheapest for large-context triage, batch analysis)
  - Fallback 2: Anthropic Claude Haiku (critique/refinement passes)

All calls are:
  - Workspace-scoped (tracked via UsageMeter)
  - Logged with provider, model, latency, token counts
  - Budget-aware (respects workspace cost limits)
  - Retryable with exponential backoff

Cost reference (per 1M tokens, approx 2026):
  - Gemini 2.0 Flash: $0.075 in / $0.30 out (cheapest)
  - OpenAI gpt-4o-mini: $0.15 in / $0.60 out
  - OpenAI gpt-4o: $2.50 in / $10.00 out (expensive, selective use)
  - Anthropic Claude 3.5 Haiku: $0.80 in / $4.00 out
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from app.integrations.llm.observability import trace_llm_call

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    """Task categories for model routing."""
    SCORING = "scoring"               # Score/rank content items
    SUMMARIZATION = "summarization"   # Summarize documents
    ANALYSIS = "analysis"             # Deep analysis (virality, gaps)
    GENERATION = "generation"         # Generate captions, scripts
    CRITIQUE = "critique"             # Review/refine content
    FACT_CHECK = "fact_check"         # Verify claims
    CLASSIFICATION = "classification" # Categorize content
    EMBEDDING = "embedding"           # Generate embeddings
    TOOL_USE = "tool_use"             # Structured tool calls


class Tier(str, Enum):
    """Cost/capability tier — abstract over specific model names.

    Routing roughly follows the 70/20/10 split from the blueprint:
      CHEAP    — bulk extract/classify/summarize. ~70% of calls.
      MID      — drafting / repurposing.          ~20% of calls.
      FRONTIER — strategy / multi-step reasoning. ~10% of calls.
    """
    CHEAP = "cheap"
    MID = "mid"
    FRONTIER = "frontier"


class Provider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    raw_response: dict | None = None


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: Provider
    model_name: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    max_tokens: int = 4096
    temperature: float = 0.7
    supports_json: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Model registry — defines available models and their costs
# ─────────────────────────────────────────────────────────────────────────────

MODELS: dict[str, ModelConfig] = {
    "gpt-4o-mini": ModelConfig(
        provider=Provider.OPENAI,
        model_name="gpt-4o-mini",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        max_tokens=16384,
    ),
    "gpt-4o": ModelConfig(
        provider=Provider.OPENAI,
        model_name="gpt-4o",
        cost_per_1m_input=2.50,
        cost_per_1m_output=10.00,
        max_tokens=16384,
    ),
    "gemini-2.0-flash": ModelConfig(
        provider=Provider.GEMINI,
        model_name="gemini-2.0-flash",
        cost_per_1m_input=0.075,
        cost_per_1m_output=0.30,
        max_tokens=8192,
    ),
    "claude-3-5-haiku": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_name="claude-3-5-haiku-latest",
        cost_per_1m_input=0.80,
        cost_per_1m_output=4.00,
        max_tokens=8192,
    ),
    "claude-3-5-sonnet": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_name="claude-3-5-sonnet-latest",
        cost_per_1m_input=3.00,
        cost_per_1m_output=15.00,
        max_tokens=8192,
    ),
    # OpenRouter — single API key, many cheap-tier models (DeepSeek, Llama, Qwen).
    # Prices are approximate 2026 spot prices; OpenRouter updates dynamically.
    "openrouter/deepseek-v3": ModelConfig(
        provider=Provider.OPENROUTER,
        model_name="deepseek/deepseek-chat",
        cost_per_1m_input=0.14,
        cost_per_1m_output=0.28,
        max_tokens=8192,
    ),
    "openrouter/llama-3.3-70b": ModelConfig(
        provider=Provider.OPENROUTER,
        model_name="meta-llama/llama-3.3-70b-instruct",
        cost_per_1m_input=0.13,
        cost_per_1m_output=0.40,
        max_tokens=8192,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Tier → ordered model chain. Used by complete(tier=...) for cost-aware routing
# decoupled from specific model names.
# ─────────────────────────────────────────────────────────────────────────────

TIER_CHAINS: dict[Tier, list[str]] = {
    Tier.CHEAP: [
        "gemini-2.0-flash",
        "openrouter/deepseek-v3",
        "gpt-4o-mini",
    ],
    Tier.MID: [
        "gpt-4o-mini",
        "claude-3-5-haiku",
        "gemini-2.0-flash",
    ],
    Tier.FRONTIER: [
        "gpt-4o",
        "claude-3-5-sonnet",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Routing policy — which model to use for which task
# ─────────────────────────────────────────────────────────────────────────────

ROUTING_POLICY: dict[TaskType, list[str]] = {
    # Cheapest first for bulk operations
    TaskType.SCORING: ["gpt-4o-mini", "gemini-2.0-flash"],
    TaskType.SUMMARIZATION: ["gpt-4o-mini", "gemini-2.0-flash"],
    TaskType.CLASSIFICATION: ["gpt-4o-mini", "gemini-2.0-flash"],

    # Primary for structured generation
    TaskType.GENERATION: ["gpt-4o-mini", "gemini-2.0-flash", "claude-3-5-haiku"],
    TaskType.TOOL_USE: ["gpt-4o-mini", "gpt-4o"],

    # Quality-first for review
    TaskType.CRITIQUE: ["gpt-4o-mini", "claude-3-5-haiku"],
    TaskType.FACT_CHECK: ["gpt-4o-mini", "claude-3-5-haiku"],

    # Deep analysis — may need stronger models
    TaskType.ANALYSIS: ["gpt-4o-mini", "gemini-2.0-flash", "gpt-4o"],
}

# Maximum retries per provider call
MAX_RETRIES = 2
RETRY_BASE_DELAY_S = 1.0


def _calculate_cost(model_config: ModelConfig, tokens_in: int, tokens_out: int) -> float:
    """Calculate cost in USD for a given token usage."""
    cost_in = (tokens_in / 1_000_000) * model_config.cost_per_1m_input
    cost_out = (tokens_out / 1_000_000) * model_config.cost_per_1m_output
    return round(cost_in + cost_out, 6)


class LLMProvider:
    """Centralized, cost-aware LLM provider with automatic fallback.

    Usage:
        provider = LLMProvider(
            openai_key="sk-...",
            gemini_key="AI...",
            anthropic_key="sk-ant-...",
        )
        response = await provider.complete(
            task_type=TaskType.GENERATION,
            messages=[{"role": "user", "content": "Write a hook"}],
            workspace_id=workspace_id,
        )
    """

    def __init__(
        self,
        *,
        openai_key: str = "",
        gemini_key: str = "",
        anthropic_key: str = "",
        openrouter_key: str = "",
        openrouter_base_url: str = "https://openrouter.ai/api/v1",
        anthropic_prompt_caching: bool = True,
    ) -> None:
        self._keys: dict[Provider, str] = {}
        if openai_key:
            self._keys[Provider.OPENAI] = openai_key
        if gemini_key:
            self._keys[Provider.GEMINI] = gemini_key
        if anthropic_key:
            self._keys[Provider.ANTHROPIC] = anthropic_key
        if openrouter_key:
            self._keys[Provider.OPENROUTER] = openrouter_key
        self._openrouter_base_url = openrouter_base_url
        self._anthropic_prompt_caching = anthropic_prompt_caching

    @property
    def available_providers(self) -> set[Provider]:
        return set(self._keys.keys())

    def _get_model_chain(self, task_type: TaskType) -> list[ModelConfig]:
        """Get ordered list of models to try for a task type, filtered by available keys."""
        model_names = ROUTING_POLICY.get(task_type, ["gpt-4o-mini"])
        chain = []
        for name in model_names:
            config = MODELS.get(name)
            if config and config.provider in self._keys:
                chain.append(config)
        if not chain:
            raise ValueError(
                f"No LLM provider available for task '{task_type.value}'. "
                f"Available providers: {self.available_providers}"
            )
        return chain

    def _get_tier_chain(self, tier: Tier) -> list[ModelConfig]:
        """Resolve a Tier to a model chain filtered by available API keys."""
        model_names = TIER_CHAINS.get(tier, [])
        chain: list[ModelConfig] = []
        for name in model_names:
            config = MODELS.get(name)
            if config and config.provider in self._keys:
                chain.append(config)
        if not chain:
            raise ValueError(
                f"No LLM provider available for tier '{tier.value}'. "
                f"Available providers: {self.available_providers}"
            )
        return chain

    async def complete(
        self,
        task_type: TaskType | None = None,
        messages: list[dict[str, str]] | None = None,
        workspace_id: uuid.UUID | None = None,
        *,
        tier: Tier | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        model_override: str | None = None,
        cache_system_prompt: bool = False,
        db_session=None,
    ) -> LLMResponse:
        """Route a completion request to the best available model.

        Exactly one of ``task_type``, ``tier``, or ``model_override`` selects
        the model chain. Tries models in priority order with automatic
        fallback. Tracks cost and latency for observability.

        Args:
            tier: Cost/capability tier. Cheaper than naming a model when the
                caller only cares about cheap/mid/frontier.
            cache_system_prompt: When True and the provider supports it
                (currently Anthropic), mark the system prompt with
                ``cache_control`` for prompt-cache reuse.
            db_session: Optional AsyncSession. If provided, writes
                UsageMeter entries and checks budget compliance.
        """
        if messages is None:
            raise ValueError("messages is required")
        if not any((task_type, tier, model_override)):
            raise ValueError("must pass task_type, tier, or model_override")

        # Budget pre-check
        if db_session and workspace_id:
            from app.services.usage_service import UsageService
            usage_svc = UsageService(db_session)
            budget = await usage_svc.check_budget(workspace_id)
            if budget["hard_stop"]:
                raise RuntimeError(
                    f"Workspace {workspace_id} budget exceeded: "
                    f"${budget['current_spend']:.2f} / ${budget['budget_limit']:.2f}"
                )

        if model_override and model_override in MODELS:
            chain = [MODELS[model_override]]
        elif tier is not None:
            chain = self._get_tier_chain(tier)
        else:
            assert task_type is not None
            chain = self._get_model_chain(task_type)

        last_error: Exception | None = None
        route_label = (
            tier.value if tier else (task_type.value if task_type else "override")
        )

        for model_config in chain:
            for attempt in range(MAX_RETRIES + 1):
                with trace_llm_call(
                    name=f"llm.complete.{route_label}",
                    model=model_config.model_name,
                    provider=model_config.provider.value,
                    task_type=task_type.value if task_type else None,
                    workspace_id=str(workspace_id) if workspace_id else None,
                    input_messages=messages,
                    metadata={
                        "tier": tier.value if tier else None,
                        "attempt": attempt + 1,
                        "cache_system_prompt": cache_system_prompt,
                    },
                ) as trace:
                    try:
                        start_time = time.monotonic()
                        response = await self._call_provider(
                            model_config=model_config,
                            messages=messages,
                            temperature=temperature or model_config.temperature,
                            max_tokens=max_tokens or model_config.max_tokens,
                            json_mode=json_mode,
                            cache_system_prompt=cache_system_prompt,
                        )
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)

                        cost = _calculate_cost(
                            model_config, response["tokens_in"], response["tokens_out"],
                        )

                        result = LLMResponse(
                            content=response["content"],
                            provider=model_config.provider.value,
                            model=model_config.model_name,
                            tokens_in=response["tokens_in"],
                            tokens_out=response["tokens_out"],
                            cost_usd=cost,
                            latency_ms=elapsed_ms,
                        )

                        trace["output"] = result.content
                        trace["tokens_in"] = result.tokens_in
                        trace["tokens_out"] = result.tokens_out
                        trace["cost_usd"] = result.cost_usd

                        logger.info(
                            "llm_call_success",
                            provider=result.provider,
                            model=result.model,
                            route=route_label,
                            tokens_in=result.tokens_in,
                            tokens_out=result.tokens_out,
                            cost_usd=result.cost_usd,
                            latency_ms=result.latency_ms,
                            workspace_id=str(workspace_id) if workspace_id else None,
                        )

                        # Record usage if session available
                        if db_session and workspace_id:
                            from app.services.usage_service import UsageService
                            usage_svc = UsageService(db_session)
                            await usage_svc.record_llm_usage(
                                workspace_id=workspace_id,
                                provider=result.provider,
                                model=result.model,
                                tokens_in=result.tokens_in,
                                tokens_out=result.tokens_out,
                                cost_usd=result.cost_usd,
                            )

                        return result

                    except Exception as exc:
                        last_error = exc
                        trace["error"] = exc
                        logger.warning(
                            "llm_call_failed",
                            provider=model_config.provider.value,
                            model=model_config.model_name,
                            route=route_label,
                            attempt=attempt + 1,
                            error=str(exc),
                        )
                        if attempt < MAX_RETRIES:
                            delay = RETRY_BASE_DELAY_S * (2 ** attempt)
                            await asyncio.sleep(delay)

        raise RuntimeError(
            f"All LLM providers failed for route '{route_label}'. "
            f"Last error: {last_error}"
        )

    async def _call_provider(
        self,
        model_config: ModelConfig,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        cache_system_prompt: bool = False,
    ) -> dict[str, Any]:
        """Dispatch to the appropriate provider SDK."""
        if model_config.provider == Provider.OPENAI:
            return await self._call_openai(
                model_config, messages, temperature, max_tokens, json_mode,
            )
        elif model_config.provider == Provider.GEMINI:
            return await self._call_gemini(
                model_config, messages, temperature, max_tokens, json_mode,
            )
        elif model_config.provider == Provider.ANTHROPIC:
            return await self._call_anthropic(
                model_config,
                messages,
                temperature,
                max_tokens,
                cache_system_prompt=cache_system_prompt,
            )
        elif model_config.provider == Provider.OPENROUTER:
            return await self._call_openrouter(
                model_config, messages, temperature, max_tokens, json_mode,
            )
        else:
            raise ValueError(f"Unknown provider: {model_config.provider}")

    async def _call_openai(
        self,
        model_config: ModelConfig,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> dict[str, Any]:
        """Call OpenAI Chat Completions API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._keys[Provider.OPENAI])

        kwargs: dict[str, Any] = {
            "model": model_config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return {
            "content": choice.message.content or "",
            "tokens_in": response.usage.prompt_tokens if response.usage else 0,
            "tokens_out": response.usage.completion_tokens if response.usage else 0,
        }

    async def _call_gemini(
        self,
        model_config: ModelConfig,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> dict[str, Any]:
        """Call Google Gemini API."""
        import google.generativeai as genai

        genai.configure(api_key=self._keys[Provider.GEMINI])

        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(model_config.model_name)

        # Convert OpenAI-style messages to Gemini format
        gemini_messages = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})

        if system_instruction:
            model = genai.GenerativeModel(
                model_config.model_name,
                system_instruction=system_instruction,
            )

        response = await asyncio.to_thread(
            model.generate_content,
            gemini_messages if gemini_messages else messages[0]["content"],
            generation_config=generation_config,
        )

        # Token counting from Gemini response
        tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else 0
        tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") else 0

        return {
            "content": response.text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    async def _call_anthropic(
        self,
        model_config: ModelConfig,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        cache_system_prompt: bool = False,
    ) -> dict[str, Any]:
        """Call Anthropic Claude API.

        When ``cache_system_prompt`` is True (and prompt caching is enabled
        on the provider), the system message is sent as a structured block
        with ``cache_control={"type": "ephemeral"}`` so repeated calls with
        the same system prompt cost ~10% of the original on cached input.
        """
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._keys[Provider.ANTHROPIC])

        # Extract system message
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": model_config.model_name,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            if cache_system_prompt and self._anthropic_prompt_caching:
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_msg,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)

        # Treat cached input as input_tokens for cost accounting; the SDK
        # exposes cache_read_input_tokens separately when caching is active.
        tokens_in = response.usage.input_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0

        return {
            "content": response.content[0].text if response.content else "",
            "tokens_in": tokens_in + cache_read + cache_write,
            "tokens_out": response.usage.output_tokens,
        }

    async def _call_openrouter(
        self,
        model_config: ModelConfig,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> dict[str, Any]:
        """Call OpenRouter via OpenAI-compatible Chat Completions API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._keys[Provider.OPENROUTER],
            base_url=self._openrouter_base_url,
        )

        kwargs: dict[str, Any] = {
            "model": model_config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return {
            "content": choice.message.content or "",
            "tokens_in": response.usage.prompt_tokens if response.usage else 0,
            "tokens_out": response.usage.completion_tokens if response.usage else 0,
        }


def create_llm_provider(
    openai_key: str = "",
    gemini_key: str = "",
    anthropic_key: str = "",
    openrouter_key: str = "",
    openrouter_base_url: str = "https://openrouter.ai/api/v1",
    anthropic_prompt_caching: bool = True,
) -> LLMProvider:
    """Factory function for creating LLMProvider from config."""
    return LLMProvider(
        openai_key=openai_key,
        gemini_key=gemini_key,
        anthropic_key=anthropic_key,
        openrouter_key=openrouter_key,
        openrouter_base_url=openrouter_base_url,
        anthropic_prompt_caching=anthropic_prompt_caching,
    )


def create_llm_provider_from_settings() -> LLMProvider:
    """Wire LLMProvider straight from app settings.

    Centralizes provider construction so call sites do not have to thread
    every key through. Use this in new code; keep ``create_llm_provider``
    for explicit/test wiring.
    """
    from app.config import get_settings

    settings = get_settings()
    return create_llm_provider(
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GEMINI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
        openrouter_key=settings.OPENROUTER_API_KEY,
        openrouter_base_url=settings.OPENROUTER_BASE_URL,
        anthropic_prompt_caching=settings.ANTHROPIC_PROMPT_CACHING,
    )
