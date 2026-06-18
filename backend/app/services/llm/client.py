"""Unified LLM Client - Abstraction over multiple LLM providers.

Phase 14: Real Agent Implementation

Provides a unified interface for calling OpenAI, Anthropic, and Google Gemini APIs.
"""
import structlog
from typing import Literal
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.config import get_settings

settings = get_settings()

log = structlog.get_logger(__name__)


class LLMResponse:
    """Unified LLM response format."""
    
    def __init__(
        self,
        content: str,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd


class LLMClient:
    """Unified LLM client with provider abstraction.
    
    Usage:
        client = LLMClient()
        response = await client.complete(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}],
        )
    """
    
    def __init__(self):
        """Initialize all LLM clients."""
        if AsyncOpenAI:
            self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai = None
        
        if AsyncAnthropic:
            self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.anthropic = None
        
        if genai:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            self.genai = None
    
    async def complete(
        self,
        provider: Literal["openai", "anthropic", "gemini"],
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Unified completion interface across all providers.
        
        Args:
            provider: LLM provider ("openai", "anthropic", "gemini")
            model: Model name
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt (overrides first system message)
        
        Returns:
            LLMResponse with content, tokens, and cost
        
        Raises:
            ValueError: If provider is unknown
            Exception: If API call fails
        """
        log.info("llm.complete.started",
                 provider=provider,
                 model=model,
                 message_count=len(messages))
        
        try:
            if provider == "openai":
                return await self._openai_complete(
                    model, messages, temperature, max_tokens, system_prompt
                )
            elif provider == "anthropic":
                return await self._anthropic_complete(
                    model, messages, temperature, max_tokens, system_prompt
                )
            elif provider == "gemini":
                return await self._gemini_complete(
                    model, messages, temperature, max_tokens, system_prompt
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")
        
        except Exception as e:
            log.error("llm.complete.failed",
                      provider=provider,
                      model=model,
                      error=str(e),
                      error_type=type(e).__name__)
            raise
    
    async def _openai_complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> LLMResponse:
        """OpenAI completion."""
        if not self.openai:
            raise RuntimeError("OpenAI client not available. Install with: pip install openai")
        
        # Override system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + [
                m for m in messages if m["role"] != "system"
            ]
        
        response = await self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.choices[0].message.content
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens
        
        # Cost calculation (approximate)
        cost_per_1k_in = 0.0025 if "gpt-4o" in model else 0.00015
        cost_per_1k_out = 0.01 if "gpt-4o" in model else 0.0006
        cost_usd = (tokens_in / 1000 * cost_per_1k_in) + (tokens_out / 1000 * cost_per_1k_out)
        
        log.info("llm.openai.completed",
                 model=model,
                 tokens_in=tokens_in,
                 tokens_out=tokens_out,
                 cost_usd=cost_usd)
        
        return LLMResponse(
            content=content,
            provider="openai",
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )
    
    async def _anthropic_complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Anthropic completion."""
        if not self.anthropic:
            raise RuntimeError("Anthropic client not available. Install with: pip install anthropic")
        
        # Extract system prompt
        system = system_prompt
        if not system:
            system_messages = [m for m in messages if m["role"] == "system"]
            if system_messages:
                system = system_messages[0]["content"]
        
        # Filter out system messages from messages list
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        response = await self.anthropic.messages.create(
            model=model,
            system=system or "",
            messages=filtered_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        
        # Cost calculation (Claude 3.5 Sonnet pricing)
        cost_per_1k_in = 0.003
        cost_per_1k_out = 0.015
        cost_usd = (tokens_in / 1000 * cost_per_1k_in) + (tokens_out / 1000 * cost_per_1k_out)
        
        log.info("llm.anthropic.completed",
                 model=model,
                 tokens_in=tokens_in,
                 tokens_out=tokens_out,
                 cost_usd=cost_usd)
        
        return LLMResponse(
            content=content,
            provider="anthropic",
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )
    
    async def _gemini_complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Google Gemini completion."""
        if not genai:
            raise RuntimeError("Google Generative AI client not available. Install with: pip install google-generativeai")
        
        # Convert messages to Gemini format
        gemini_messages = []
        system = system_prompt
        
        for msg in messages:
            if msg["role"] == "system":
                if not system:
                    system = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})
        
        # Create model
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
        )
        
        # Generate
        response = await gemini_model.generate_content_async(
            gemini_messages,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        
        content = response.text
        
        # Token counting (approximate)
        tokens_in = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
        tokens_out = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
        
        # Cost calculation (Gemini 1.5 Pro pricing)
        if "flash" in model.lower():
            cost_per_1k_in = 0.000075
            cost_per_1k_out = 0.0003
        else:
            cost_per_1k_in = 0.00125
            cost_per_1k_out = 0.005
        
        cost_usd = (tokens_in / 1000 * cost_per_1k_in) + (tokens_out / 1000 * cost_per_1k_out)
        
        log.info("llm.gemini.completed",
                 model=model,
                 tokens_in=tokens_in,
                 tokens_out=tokens_out,
                 cost_usd=cost_usd)
        
        return LLMResponse(
            content=content,
            provider="gemini",
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )


# Global client instance
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
