"""Twitter/X platform service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from urllib.parse import quote

import httpx

from app.services.platforms.base import BasePlatformService
from app.exceptions import PlatformError

_BASE = "https://api.twitter.com/2"
_MAX_TWEET = 280


class TwitterService(BasePlatformService):
    platform_name = "x"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._access_secret = access_secret

    def _oauth1_header(self, method: str, url: str) -> str:
        """Build OAuth 1.0a Authorization header."""
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        params = {
            "oauth_consumer_key": self._api_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": self._access_token,
            "oauth_version": "1.0",
        }
        param_string = "&".join(
            f"{quote(k)}={quote(str(v))}" for k, v in sorted(params.items())
        )
        base_string = f"{method}&{quote(url)}&{quote(param_string)}"
        signing_key = f"{quote(self._api_secret)}&{quote(self._access_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        params["oauth_signature"] = signature
        return "OAuth " + ", ".join(
            f'{k}="{quote(str(v))}"' for k, v in params.items()
        )

    async def post_tweet(self, text: str) -> dict:
        url = f"{_BASE}/tweets"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                return await self._post_with_retry(
                    client,
                    url,
                    json={"text": text[:_MAX_TWEET]},
                    headers={
                        "Authorization": self._oauth1_header("POST", url),
                        "Content-Type": "application/json",
                    },
                )
            except PlatformError:
                raise
            except Exception as exc:
                raise self._wrap_error(exc, "post_tweet")
