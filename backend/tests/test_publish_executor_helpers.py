"""Unit tests for publish_executor helpers — idempotency + auth detection.

Full integration of `_execute_single_job` requires a Postgres-backed session and
is covered by the existing DB-bound tests; these tests pin the pure-Python
predicates that decide whether a retry needs a token refresh.
"""
from __future__ import annotations

from app.integrations.platforms.adapters import PublishResult
from app.services import publish_executor


def test_is_auth_failure_success_returns_false():
    assert publish_executor._is_auth_failure(PublishResult(success=True)) is False


def test_is_auth_failure_401_response_code():
    assert publish_executor._is_auth_failure(
        PublishResult(success=False, provider_response_code=401)
    ) is True


def test_is_auth_failure_token_expired_class():
    assert publish_executor._is_auth_failure(
        PublishResult(success=False, failure_class="token_expired")
    ) is True


def test_is_auth_failure_auth_class_case_insensitive():
    assert publish_executor._is_auth_failure(
        PublishResult(success=False, failure_class="AUTH")
    ) is True


def test_is_auth_failure_other_failure_class_returns_false():
    assert publish_executor._is_auth_failure(
        PublishResult(success=False, failure_class="rate_limit", provider_response_code=429)
    ) is False


def test_is_auth_failure_5xx_not_auth():
    assert publish_executor._is_auth_failure(
        PublishResult(success=False, provider_response_code=503)
    ) is False
