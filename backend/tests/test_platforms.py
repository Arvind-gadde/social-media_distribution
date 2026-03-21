import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.platforms.twitter import TwitterService
from app.exceptions import PlatformError
from tenacity import RetryError

@pytest.fixture
def twitter_service():
    return TwitterService("key", "secret", "token", "tsecret")

@pytest.mark.asyncio
async def test_twitter_post_success(twitter_service):
    with patch("app.services.platforms.twitter.httpx.AsyncClient.__aenter__") as enter_mock:
        client_mock = MagicMock()
        enter_mock.return_value = client_mock
        
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"id": "123"}
        
        # AsyncMock for the awaitable 'post' method
        client_mock.post = AsyncMock(return_value=response_mock)
        
        res = await twitter_service.post_tweet("Hello world")
        assert res == {"id": "123"}
        
        client_mock.post.assert_called_once()
        (url,), kwargs = client_mock.post.call_args
        assert url == "https://api.twitter.com/2/tweets"
        assert kwargs["json"] == {"text": "Hello world"}
        assert "Authorization" in kwargs["headers"]
        assert "OAuth" in kwargs["headers"]["Authorization"]

@pytest.mark.asyncio
async def test_twitter_post_retry_exhausted(twitter_service):
    with patch("app.services.platforms.twitter.httpx.AsyncClient.__aenter__") as enter_mock:
        client_mock = AsyncMock()
        enter_mock.return_value = client_mock
        
        client_mock.post.side_effect = httpx.TimeoutException("Timeout")
        
        with patch("tenacity.nap.time.sleep"):
            with pytest.raises(PlatformError, match="post_tweet: Timeout"):
                await twitter_service.post_tweet("Hello world")
        
        assert client_mock.post.call_count == 3

@pytest.mark.asyncio
async def test_twitter_post_server_error(twitter_service):
    with patch("app.services.platforms.twitter.httpx.AsyncClient.__aenter__") as enter_mock:
        client_mock = AsyncMock()
        enter_mock.return_value = client_mock
        
        response_mock = MagicMock()
        response_mock.status_code = 500
        response_mock.request = MagicMock()
        client_mock.post.return_value = response_mock
        
        with patch("tenacity.nap.time.sleep"):
            with pytest.raises(PlatformError, match="Server error 500"):
                await twitter_service.post_tweet("Hello world")

@pytest.mark.asyncio
async def test_twitter_post_general_error(twitter_service):
    with patch("app.services.platforms.twitter.httpx.AsyncClient.__aenter__") as enter_mock:
        client_mock = AsyncMock()
        enter_mock.return_value = client_mock
        
        client_mock.post.side_effect = ValueError("Bad value")
        
        with pytest.raises(PlatformError, match="post_tweet: Bad value"):
            await twitter_service.post_tweet("Hello world")
