import pytest
from unittest.mock import AsyncMock, patch
from app.services.cache_service import CacheService

@pytest.fixture
def mock_redis():
    with patch("app.services.cache_service.aioredis.from_url") as mock_from_url:
        mock_instance = AsyncMock()
        mock_from_url.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def cache_service(mock_redis):
    return CacheService()

@pytest.mark.asyncio
async def test_set_success(cache_service, mock_redis):
    await cache_service.set("key_1", {"foo": "bar"}, 60)
    mock_redis.setex.assert_called_once_with("key_1", 60, '{"foo": "bar"}')

@pytest.mark.asyncio
async def test_set_failure_swallowed(cache_service, mock_redis):
    mock_redis.setex.side_effect = Exception("Redis down")
    # Should not raise exception
    await cache_service.set("key_1", "value")

@pytest.mark.asyncio
async def test_get_success(cache_service, mock_redis):
    mock_redis.get.return_value = '{"success": true}'
    result = await cache_service.get("my_key")
    assert result == {"success": True}

@pytest.mark.asyncio
async def test_get_not_found(cache_service, mock_redis):
    mock_redis.get.return_value = None
    result = await cache_service.get("null_key")
    assert result is None

@pytest.mark.asyncio
async def test_get_failure_swallowed(cache_service, mock_redis):
    mock_redis.get.side_effect = Exception("Timeout")
    result = await cache_service.get("bad_key")
    assert result is None

@pytest.mark.asyncio
async def test_delete_success(cache_service, mock_redis):
    await cache_service.delete("key_1")
    mock_redis.delete.assert_called_once_with("key_1")

@pytest.mark.asyncio
async def test_delete_failure_swallowed(cache_service, mock_redis):
    mock_redis.delete.side_effect = Exception("Fail")
    await cache_service.delete("key_1")

@pytest.mark.asyncio
async def test_exists(cache_service, mock_redis):
    mock_redis.exists.return_value = 1
    assert await cache_service.exists("k") is True
    
    mock_redis.exists.return_value = 0
    assert await cache_service.exists("k2") is False

@pytest.mark.asyncio
async def test_exists_failure_swallowed(cache_service, mock_redis):
    mock_redis.exists.side_effect = Exception("Error")
    assert await cache_service.exists("key") is False

@pytest.mark.asyncio
async def test_typed_helpers(cache_service, mock_redis):
    # test get_cached_user
    mock_redis.get.return_value = '{"id": "user1"}'
    user = await cache_service.get_cached_user("user1")
    assert user["id"] == "user1"
    
    # test cache_user
    await cache_service.cache_user("user2", {"id": "user2"})
    mock_redis.setex.assert_called_with("user:user2", 1800, '{"id": "user2"}')
    
    # test invalidate_user
    await cache_service.invalidate_user("user2")
    mock_redis.delete.assert_called_with("user:user2")

    # test blacklist_jti
    await cache_service.blacklist_jti("token123", 300)
    mock_redis.setex.assert_called_with("jti_blacklist:token123", 300, "true")

    # test is_jti_blacklisted
    mock_redis.exists.return_value = 1
    is_blacklisted = await cache_service.is_jti_blacklisted("token123")
    assert is_blacklisted is True

    # test push subscriptions
    await cache_service.save_push_subscription("u1", {"endpoint": "url"})
    mock_redis.setex.assert_called_with("push_sub:u1", 86400 * 30, '{"endpoint": "url"}')
    
    mock_redis.get.return_value = '{"endpoint": "url"}'
    sub = await cache_service.get_push_subscription("u1")
    assert sub["endpoint"] == "url"
