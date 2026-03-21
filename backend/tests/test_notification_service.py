import pytest
from unittest.mock import AsyncMock, patch
from app.services.notification_service import NotificationService
from app.services.cache_service import CacheService

@pytest.fixture
def mock_cache():
    return AsyncMock(spec=CacheService)

@pytest.fixture
def notification_service(mock_cache):
    return NotificationService(cache=mock_cache)

@pytest.mark.asyncio
async def test_save_subscription(notification_service, mock_cache):
    await notification_service.save_subscription("user_1", "https://push.com/abc", {"p": "v"})
    mock_cache.save_push_subscription.assert_called_once_with(
        "user_1",
        {"endpoint": "https://push.com/abc", "keys": {"p": "v"}}
    )

@pytest.mark.asyncio
async def test_remove_subscription(notification_service, mock_cache):
    await notification_service.remove_subscription("user_1")
    mock_cache.delete.assert_called_once_with("push_sub:user_1")

@patch("app.services.notification_service.settings.VAPID_PRIVATE_KEY", "fake_key")
@patch("app.services.notification_service.settings.VAPID_EMAIL", "test@test.com")
@patch("pywebpush.webpush")
@pytest.mark.asyncio
async def test_send_success(mock_webpush, notification_service, mock_cache):
    mock_cache.get_push_subscription.return_value = {"endpoint": "https://push.com/abc", "keys": {}}
    
    await notification_service.send("user_1", "Hello", "World msg")
    
    mock_cache.get_push_subscription.assert_called_once_with("user_1")
    mock_webpush.assert_called_once()
    args = mock_webpush.call_args[1]
    assert args["subscription_info"] == {"endpoint": "https://push.com/abc", "keys": {}}
    assert "Hello" in args["data"]
    assert "World msg" in args["data"]
    assert args["vapid_private_key"] == "fake_key"
    assert args["vapid_claims"] == {"sub": "mailto:test@test.com"}

@patch("app.services.notification_service.settings.VAPID_PRIVATE_KEY", "fake_key")
@patch("pywebpush.webpush")
@pytest.mark.asyncio
async def test_send_no_sub(mock_webpush, notification_service, mock_cache):
    mock_cache.get_push_subscription.return_value = None
    await notification_service.send("user_1", "Hello", "World msg")
    mock_webpush.assert_not_called()

@patch("app.services.notification_service.settings.VAPID_PRIVATE_KEY", None)
@patch("pywebpush.webpush")
@pytest.mark.asyncio
async def test_send_no_vapid_key(mock_webpush, notification_service, mock_cache):
    mock_cache.get_push_subscription.return_value = {"endpoint": "abc"}
    await notification_service.send("user_1", "Hello", "World msg")
    mock_webpush.assert_not_called()

@patch("app.services.notification_service.settings.VAPID_PRIVATE_KEY", "fake_key")
@patch("pywebpush.webpush")
@pytest.mark.asyncio
async def test_send_failure_swallowed(mock_webpush, notification_service, mock_cache):
    mock_cache.get_push_subscription.return_value = {"endpoint": "abc"}
    mock_webpush.side_effect = Exception("Push server rejected")
    await notification_service.send("user_1", "Hello", "World msg")
