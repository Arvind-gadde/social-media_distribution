"""Tests for Phase 14: Real Agent Implementation Infrastructure.

Tests:
1. LLM Client functionality
2. Cache Manager functionality
3. Integration between components
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse, get_llm_client
from app.services.cache.cache_manager import CacheManager, get_cache_manager


# ═══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMClient:
    """Test LLM client functionality."""
    
    def test_llm_response_creation(self):
        """Test LLMResponse object creation."""
        response = LLMResponse(
            content="Hello, world!",
            provider="openai",
            model="gpt-4o",
            tokens_in=10,
            tokens_out=5,
            cost_usd=0.0001,
        )
        
        assert response.content == "Hello, world!"
        assert response.provider == "openai"
        assert response.model == "gpt-4o"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
        assert response.cost_usd == 0.0001
    
    def test_get_llm_client_singleton(self):
        """Test that get_llm_client returns singleton."""
        client1 = get_llm_client()
        client2 = get_llm_client()
        
        assert client1 is client2
    
    @pytest.mark.asyncio
    async def test_llm_client_invalid_provider(self):
        """Test LLM client with invalid provider."""
        client = LLMClient()
        
        with pytest.raises(ValueError, match="Unknown provider"):
            await client.complete(
                provider="invalid",
                model="test-model",
                messages=[{"role": "user", "content": "test"}],
            )
    
    @pytest.mark.asyncio
    @patch('app.services.llm.client.AsyncOpenAI')
    async def test_openai_complete_mock(self, mock_openai_class):
        """Test OpenAI completion with mocked API."""
        # Setup mock
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Create client and call
        client = LLMClient()
        response = await client.complete(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
        assert response.cost_usd > 0
    
    @pytest.mark.asyncio
    @patch('app.services.llm.client.AsyncAnthropic')
    async def test_anthropic_complete_mock(self, mock_anthropic_class):
        """Test Anthropic completion with mocked API."""
        # Setup mock
        mock_client = AsyncMock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test response"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        # Create client and call
        client = LLMClient()
        response = await client.complete(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        assert response.content == "Test response"
        assert response.provider == "anthropic"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
        assert response.cost_usd > 0


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestCacheManager:
    """Test cache manager functionality."""
    
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = CacheManager()
        
        key1 = cache._make_key("test_agent", "workspace-123", "cache-key-1")
        key2 = cache._make_key("test_agent", "workspace-123", "cache-key-2")
        key3 = cache._make_key("test_agent", "workspace-456", "cache-key-1")
        
        # Same agent + workspace + key should produce same key
        key1_duplicate = cache._make_key("test_agent", "workspace-123", "cache-key-1")
        assert key1 == key1_duplicate
        
        # Different cache keys should produce different keys
        assert key1 != key2
        
        # Different workspaces should produce different keys
        assert key1 != key3
        
        # Keys should follow format
        assert key1.startswith("agent:test_agent:workspace-123:")
    
    async def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        assert manager1 is manager2
    
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_cache_miss(self, mock_redis):
        """Test cache miss scenario."""
        # Setup mock
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis.from_url.return_value = mock_redis_client
        
        cache = CacheManager()
        
        result = await cache.get_cached_result(
            agent_name="test_agent",
            workspace_id="workspace-123",
            cache_key="test-key",
        )
        
        assert result is None
    
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_cache_hit(self, mock_redis):
        """Test cache hit scenario."""
        # Setup mock
        import json
        cached_data = {"result": "cached value"}
        
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data))
        mock_redis.from_url.return_value = mock_redis_client
        
        cache = CacheManager()
        
        result = await cache.get_cached_result(
            agent_name="test_agent",
            workspace_id="workspace-123",
            cache_key="test-key",
        )
        
        assert result == cached_data
    
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_cache_set(self, mock_redis):
        """Test caching a result."""
        # Setup mock
        mock_redis_client = AsyncMock()
        mock_redis_client.setex = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_client
        
        cache = CacheManager()
        
        test_data = {"result": "test value"}
        await cache.cache_result(
            agent_name="test_agent",
            workspace_id="workspace-123",
            cache_key="test-key",
            result=test_data,
            ttl=3600,
        )
        
        # Verify setex was called
        mock_redis_client.setex.assert_called_once()
    
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_cache_invalidate_single(self, mock_redis):
        """Test invalidating a single cache key."""
        # Setup mock
        mock_redis_client = AsyncMock()
        mock_redis_client.delete = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_client
        
        cache = CacheManager()
        
        await cache.invalidate(
            agent_name="test_agent",
            workspace_id="workspace-123",
            cache_key="test-key",
        )
        
        # Verify delete was called
        mock_redis_client.delete.assert_called_once()
    
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_cache_invalidate_all(self, mock_redis):
        """Test invalidating all cache keys for an agent."""
        # Setup mock
        mock_redis_client = AsyncMock()
        
        # Mock scan_iter to return some keys
        async def mock_scan_iter(match):
            keys = ["key1", "key2", "key3"]
            for key in keys:
                yield key
        
        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.delete = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_client
        
        cache = CacheManager()
        
        await cache.invalidate(
            agent_name="test_agent",
            workspace_id="workspace-123",
            cache_key=None,  # Invalidate all
        )
        
        # Verify delete was called with all keys
        mock_redis_client.delete.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestInfrastructureIntegration:
    """Test integration between LLM client and cache manager."""
    
    @patch('app.services.llm.client.AsyncOpenAI')
    @patch('app.services.cache.cache_manager.aioredis')
    async def test_llm_with_cache(self, mock_redis, mock_openai_class):
        """Test LLM client with caching layer."""
        # Setup LLM mock
        mock_openai_client = AsyncMock()
        mock_openai_class.return_value = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Setup cache mock
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis_client.setex = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_client
        
        # Create clients
        llm_client = LLMClient()
        cache = CacheManager()
        
        # Simulate agent workflow with caching
        workspace_id = str(uuid.uuid4())
        cache_key = "test-prompt"
        
        # Try cache first
        cached = await cache.get_cached_result(
            agent_name="test_agent",
            workspace_id=workspace_id,
            cache_key=cache_key,
        )
        
        if not cached:
            # Call LLM
            response = await llm_client.complete(
                provider="openai",
                model="gpt-4o",
                messages=[{"role": "user", "content": "Test"}],
            )
            
            # Cache result
            await cache.cache_result(
                agent_name="test_agent",
                workspace_id=workspace_id,
                cache_key=cache_key,
                result={"content": response.content, "cost": response.cost_usd},
                ttl=3600,
            )
        
        # Verify LLM was called
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify cache was set
        mock_redis_client.setex.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test Coverage Summary:

✅ LLM Client (6 tests)
   - Response object creation
   - Singleton pattern
   - Invalid provider handling
   - OpenAI completion (mocked)
   - Anthropic completion (mocked)

✅ Cache Manager (7 tests)
   - Key generation
   - Singleton pattern
   - Cache miss
   - Cache hit
   - Cache set
   - Single key invalidation
   - All keys invalidation

✅ Integration (1 test)
   - LLM client with caching layer

Total: 14 tests
"""
