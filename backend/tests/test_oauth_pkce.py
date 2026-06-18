"""Tests for OAuth PKCE wiring and state round-tripping."""
from __future__ import annotations

import base64
import hashlib
import os
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

# Ensure required env vars are present before importing settings-bound modules.
os.environ.setdefault("APP_SECRET_KEY", "test-app-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test/test")

from app.api.v1 import oauth as oauth_api  # noqa: E402
from app.services.oauth.base import derive_pkce_challenge  # noqa: E402
from app.services.oauth.twitter import TwitterOAuth  # noqa: E402


def test_derive_pkce_challenge_matches_rfc7636():
    # RFC 7636 Appendix B test vector.
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert derive_pkce_challenge(verifier) == expected


def test_state_round_trip_preserves_verifier():
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    verifier = oauth_api._generate_pkce_verifier()

    state = oauth_api._create_oauth_state(
        workspace_id, user_id, code_verifier=verifier
    )
    parsed = oauth_api._parse_oauth_state(state)

    assert parsed["workspace_id"] == workspace_id
    assert parsed["code_verifier"] == verifier


def test_state_without_verifier_round_trip():
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    state = oauth_api._create_oauth_state(workspace_id, user_id)
    parsed = oauth_api._parse_oauth_state(state)
    assert parsed["workspace_id"] == workspace_id
    assert parsed["code_verifier"] is None


def test_state_rejects_tampering():
    state = oauth_api._create_oauth_state(uuid.uuid4(), uuid.uuid4())
    payload, sig = state.split(".", 1)
    tampered = f"{payload[:-1]}A.{sig}" if payload[-1] != "A" else f"{payload[:-1]}B.{sig}"
    with pytest.raises(ValueError):
        oauth_api._parse_oauth_state(tampered)


def test_twitter_auth_url_uses_s256_challenge():
    verifier = oauth_api._generate_pkce_verifier()
    service = TwitterOAuth()
    url = service.get_authorization_url(
        redirect_uri="https://example.com/cb",
        state="state-token",
        code_verifier=verifier,
    )
    params = parse_qs(urlparse(url).query)
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"] == [derive_pkce_challenge(verifier)]
    assert "plain" not in params.get("code_challenge_method", [])


def test_twitter_auth_url_drops_pkce_when_no_verifier():
    service = TwitterOAuth()
    url = service.get_authorization_url(
        redirect_uri="https://example.com/cb",
        state="state-token",
    )
    params = parse_qs(urlparse(url).query)
    # Hardcoded "plain"/"challenge" must no longer appear.
    assert params.get("code_challenge") != ["challenge"]
    assert params.get("code_challenge_method") != ["plain"]


def test_pkce_platforms_registry_only_includes_twitter():
    # Guard against accidentally enabling PKCE for platforms whose flows
    # haven't been wired through end-to-end.
    assert oauth_api._PKCE_PLATFORMS == {"twitter"}
