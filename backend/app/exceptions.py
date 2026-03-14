"""Typed exception hierarchy — every error has a code, message, and HTTP status."""

from __future__ import annotations


class AppError(Exception):
    """Base application error. Always has a structured representation."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str = "") -> None:
        detail = f"{resource} not found" + (f": {identifier}" if identifier else "")
        super().__init__(detail, "NOT_FOUND", 404)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR", 422)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFLICT", 409)


class MediaError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "MEDIA_ERROR", 400)


class PlatformError(AppError):
    def __init__(self, platform: str, message: str) -> None:
        super().__init__(f"[{platform}] {message}", "PLATFORM_ERROR", 502)


class StorageError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "STORAGE_ERROR", 500)


class RateLimitError(AppError):
    def __init__(self) -> None:
        super().__init__("Too many requests", "RATE_LIMIT_EXCEEDED", 429)


class AIServiceError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "AI_SERVICE_ERROR", 503)
