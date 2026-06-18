"""Platform integration package — publishing adapters and analytics sync."""
from app.integrations.platforms.adapters import (
    PlatformAdapter,
    PublishPayload,
    PublishResult,
    get_adapter,
    ADAPTERS,
)

__all__ = [
    "PlatformAdapter",
    "PublishPayload",
    "PublishResult",
    "get_adapter",
    "ADAPTERS",
]
