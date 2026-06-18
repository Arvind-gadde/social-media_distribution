"""Tests for tiered LLM routing, OpenRouter dispatch, prompt caching, and Langfuse tracing."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.llm.provider import (
    MODELS,
    TIER_CHAINS,
    LLMProvider,
    Provider,
    TaskType,
    Tier,
    create_llm_provider,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tier resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestTierResolution:
    def test_each_tier_has_models(self):
        for tier in Tier:
            assert TIER_CHAINS[tier], f"tier {tier} has empty chain"

    def test_cheap_tier_starts_with_cheapest_available(self):
        p = create_llm_provider(gemini_key="g", openai_key="o", openrouter_key="r")
        chain = p._get_tier_chain(Tier.CHEAP)
        # gemini-2.0-flash is cheapest in registry
        assert chain[0].model_name == "gemini-2.0-flash"

    def test_tier_chain_filters_to_available_providers(self):
        p = create_llm_provider(openai_key="o")  # no gemini, no anthropic, no openrouter
        chain = p._get_tier_chain(Tier.CHEAP)
        assert all(c.provider == Provider.OPENAI for c in chain)
        assert chain  # gpt-4o-mini still resolvable

    def test_tier_chain_raises_when_no_provider(self):
        p = create_llm_provider()  # no keys at all
        with pytest.raises(ValueError, match="No LLM provider available for tier"):
            p._get_tier_chain(Tier.FRONTIER)

    def test_frontier_tier_uses_gpt4o(self):
        p = create_llm_provider(openai_key="o", anthropic_key="a")
        chain = p._get_tier_chain(Tier.FRONTIER)
        assert chain[0].model_name == "gpt-4o"


# ─────────────────────────────────────────────────────────────────────────────
# Model registry & cost
# ─────────────────────────────────────────────────────────────────────────────

class TestModelRegistry:
    def test_openrouter_models_registered(self):
        assert "openrouter/deepseek-v3" in MODELS
        assert MODELS["openrouter/deepseek-v3"].provider == Provider.OPENROUTER

    def test_claude_sonnet_registered(self):
        assert "claude-3-5-sonnet" in MODELS
        assert MODELS["claude-3-5-sonnet"].provider == Provider.ANTHROPIC


# ─────────────────────────────────────────────────────────────────────────────
# complete() input validation
# ─────────────────────────────────────────────────────────────────────────────

class TestCompleteValidation:
    @pytest.mark.asyncio
    async def test_complete_requires_routing_arg(self):
        p = create_llm_provider(openai_key="o")
        with pytest.raises(ValueError, match="must pass"):
            await p.complete(messages=[{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_complete_requires_messages(self):
        p = create_llm_provider(openai_key="o")
        with pytest.raises(ValueError, match="messages is required"):
            await p.complete(task_type=TaskType.GENERATION)


# ─────────────────────────────────────────────────────────────────────────────
# Tier dispatch end-to-end (mocked SDK)
# ─────────────────────────────────────────────────────────────────────────────

class TestTierDispatch:
    @pytest.mark.asyncio
    async def test_tier_cheap_calls_first_model_in_chain(self):
        p = create_llm_provider(openai_key="o")
        with patch.object(
            p, "_call_provider", new=AsyncMock(return_value={
                "content": "ok", "tokens_in": 10, "tokens_out": 5,
            }),
        ) as mock:
            result = await p.complete(
                tier=Tier.MID,
                messages=[{"role": "user", "content": "hi"}],
            )
        assert result.content == "ok"
        # First call argument is the resolved model_config
        called_cfg = mock.call_args.kwargs["model_config"]
        assert called_cfg.model_name == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_falls_back_to_next_model_on_failure(self):
        p = create_llm_provider(openai_key="o", anthropic_key="a")
        attempts: list[str] = []

        async def flaky(**kw):
            attempts.append(kw["model_config"].model_name)
            if kw["model_config"].model_name == "gpt-4o-mini":
                raise RuntimeError("rate limited")
            return {"content": "ok", "tokens_in": 1, "tokens_out": 1}

        with patch.object(p, "_call_provider", new=flaky):
            with patch("asyncio.sleep", new=AsyncMock()):
                result = await p.complete(
                    tier=Tier.MID,
                    messages=[{"role": "user", "content": "hi"}],
                )
        assert result.model == "claude-3-5-haiku-latest"
        # gpt-4o-mini retried twice (MAX_RETRIES=2 + 1 initial = 3), then haiku
        assert attempts.count("gpt-4o-mini") == 3
        assert "claude-3-5-haiku-latest" in attempts


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic prompt caching
# ─────────────────────────────────────────────────────────────────────────────

class TestAnthropicPromptCaching:
    @pytest.mark.asyncio
    async def test_cache_system_prompt_sends_cache_control(self):
        p = create_llm_provider(anthropic_key="a", anthropic_prompt_caching=True)

        captured: dict = {}

        class FakeClient:
            class messages:
                @staticmethod
                async def create(**kwargs):
                    captured.update(kwargs)
                    usage = MagicMock()
                    usage.input_tokens = 10
                    usage.output_tokens = 5
                    usage.cache_read_input_tokens = 0
                    usage.cache_creation_input_tokens = 0
                    content = [MagicMock()]
                    content[0].text = "hi"
                    resp = MagicMock()
                    resp.content = content
                    resp.usage = usage
                    return resp

        with patch("anthropic.AsyncAnthropic", return_value=FakeClient()):
            await p.complete(
                model_override="claude-3-5-haiku",
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hi"},
                ],
                cache_system_prompt=True,
            )

        # System now is a structured block list, not a plain string
        assert isinstance(captured["system"], list)
        assert captured["system"][0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    async def test_caching_disabled_passes_plain_system(self):
        p = create_llm_provider(anthropic_key="a", anthropic_prompt_caching=False)

        captured: dict = {}

        class FakeClient:
            class messages:
                @staticmethod
                async def create(**kwargs):
                    captured.update(kwargs)
                    usage = MagicMock()
                    usage.input_tokens = 10
                    usage.output_tokens = 5
                    usage.cache_read_input_tokens = 0
                    usage.cache_creation_input_tokens = 0
                    content = [MagicMock()]
                    content[0].text = "hi"
                    resp = MagicMock()
                    resp.content = content
                    resp.usage = usage
                    return resp

        with patch("anthropic.AsyncAnthropic", return_value=FakeClient()):
            await p.complete(
                model_override="claude-3-5-haiku",
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hi"},
                ],
                cache_system_prompt=True,  # asked, but disabled at provider level
            )

        assert captured["system"] == "You are helpful."


# ─────────────────────────────────────────────────────────────────────────────
# OpenRouter dispatch
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenRouterDispatch:
    @pytest.mark.asyncio
    async def test_openrouter_uses_openai_compatible_base_url(self):
        p = create_llm_provider(openrouter_key="or", openrouter_base_url="https://example/api")

        captured: dict = {}

        class FakeChat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    captured.update(kwargs)
                    msg = MagicMock(); msg.content = "ok"
                    choice = MagicMock(); choice.message = msg
                    usage = MagicMock(); usage.prompt_tokens = 5; usage.completion_tokens = 3
                    resp = MagicMock(); resp.choices = [choice]; resp.usage = usage
                    return resp

        class FakeClient:
            chat = FakeChat

        with patch("openai.AsyncOpenAI") as ctor:
            ctor.return_value = FakeClient()
            await p.complete(
                model_override="openrouter/deepseek-v3",
                messages=[{"role": "user", "content": "hi"}],
            )
            # Constructor must receive base_url override
            ctor.assert_called_with(api_key="or", base_url="https://example/api")
        assert captured["model"] == "deepseek/deepseek-chat"


# ─────────────────────────────────────────────────────────────────────────────
# Langfuse no-op when disabled
# ─────────────────────────────────────────────────────────────────────────────

class TestLangfuseNoOp:
    def test_trace_llm_call_yields_record_when_disabled(self):
        from app.integrations.llm import observability

        # Force re-init with disabled state
        observability._client = None
        observability._init_attempted = False
        with patch("app.integrations.llm.observability.get_settings") as gs:
            gs.return_value.has_langfuse = False
            with observability.trace_llm_call(
                name="t",
                model="m",
                provider="p",
                task_type=None,
                workspace_id=None,
            ) as rec:
                rec["output"] = "x"
                rec["tokens_in"] = 1
            # Did not raise; record is a plain dict
            assert rec["output"] == "x"
