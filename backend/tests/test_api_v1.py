import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from unittest.mock import AsyncMock

from app.main import app
from app.api.deps import get_cache, get_current_user
from app.services.cache_service import CacheService
from app.models.models import User

@pytest.fixture
def mock_cache():
    return AsyncMock(spec=CacheService)

@pytest.fixture
def mock_user():
    user = User(
        id=uuid4(),
        email="test@example.com",
        is_active=True
    )
    return user

@pytest_asyncio.fixture
async def client(mock_cache, mock_user):
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_notifications_subscribe(client, mock_cache, mock_user):
    payload = {
        "endpoint": "https://push.com/endpoint",
        "keys": {"p256dh": "pubkey", "auth": "authsecret"}
    }
    resp = await client.post("/api/v1/notifications/subscribe", json=payload)
    
    assert resp.status_code == 201
    assert resp.json() == {"status": "subscribed"}
    
    mock_cache.save_push_subscription.assert_called_once_with(
        str(mock_user.id),
        {"endpoint": "https://push.com/endpoint", "keys": {"p256dh": "pubkey", "auth": "authsecret"}}
    )

@pytest.mark.asyncio
async def test_notifications_unsubscribe(client, mock_cache, mock_user):
    resp = await client.delete("/api/v1/notifications/unsubscribe")
    
    assert resp.status_code == 200
    assert resp.json() == {"status": "unsubscribed"}
    
    mock_cache.delete.assert_called_once_with(f"push_sub:{mock_user.id}")

@pytest.mark.asyncio
async def test_notifications_subscribe_validation_error(client, mock_cache, mock_user):
    # Missing endpoint which is required by PushSubscriptionRequest
    payload = {
        "keys": {"p256dh": "pubkey", "auth": "authsecret"}
    }
    resp = await client.post("/api/v1/notifications/subscribe", json=payload)
    
    assert resp.status_code == 422
    mock_cache.save_push_subscription.assert_not_called()
