"""Platform service base class with circuit breaker and retry logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.exceptions import PlatformError

logger = structlog.get_logger(__name__)

_RETRYABLE = (httpx.TimeoutException, httpx.NetworkError)


class BasePlatformService(ABC):
    """
    Abstract base for platform integrations.
    Provides retry logic and structured error wrapping.
    All platform-specific services must extend this.
    """

    platform_name: str = "unknown"

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        **kwargs: Any,
    ) -> dict:
        """POST with exponential backoff retry on transient errors."""
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        ):
            with attempt:
                resp = await client.post(url, **kwargs)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                return resp.json()
        raise PlatformError(self.platform_name, "Retry exhausted")

    def _wrap_error(self, exc: Exception, context: str) -> PlatformError:
        logger.error(
            "platform_error",
            platform=self.platform_name,
            context=context,
            error=str(exc),
        )
        return PlatformError(self.platform_name, f"{context}: {exc}")
