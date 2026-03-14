"""Tests for AuthService — register, login, Google OAuth, token issuance."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.exceptions import AuthenticationError, ConflictError
from app.models.models import User
from app.services.auth_service import AuthService


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_user(**kwargs) -> User:
    defaults = dict(
        id=__import__("uuid").uuid4(),
        email="arun@example.com",
        name="Arun",
        is_active=True,
        password_hash=None,
        google_id=None,
        encrypted_platform_tokens={},
        connected_platforms=[],
    )
    defaults.update(kwargs)
    u = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def _make_service(user_repo=None, cache=None):
    repo = user_repo or AsyncMock()
    c = cache or AsyncMock()
    return AuthService(repo, c), repo, c


# ── Password hashing ──────────────────────────────────────────────────────

def test_hash_and_verify_password():
    hashed = AuthService.hash_password("Secret1")
    assert AuthService.verify_password("Secret1", hashed) is True
    assert AuthService.verify_password("Wrong1", hashed) is False


def test_verify_password_handles_garbage_hash():
    """Must not raise on malformed stored hash."""
    assert AuthService.verify_password("anything", "not-a-hash") is False


# ── Register ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_user():
    svc, repo, _ = _make_service()
    repo.get_by_email = AsyncMock(return_value=None)
    new_user = _make_user(email="new@example.com", name="New User")
    repo.save = AsyncMock(return_value=new_user)

    user = await svc.register("new@example.com", "Password1", "New User")

    repo.save.assert_awaited_once()
    saved: User = repo.save.call_args[0][0]
    assert saved.email == "new@example.com"
    assert saved.password_hash is not None
    assert AuthService.verify_password("Password1", saved.password_hash)


@pytest.mark.asyncio
async def test_register_raises_on_duplicate_email():
    svc, repo, _ = _make_service()
    repo.get_by_email = AsyncMock(return_value=_make_user())

    with pytest.raises(ConflictError, match="already exists"):
        await svc.register("arun@example.com", "Password1", "Arun")


@pytest.mark.asyncio
async def test_register_lowercases_email():
    svc, repo, _ = _make_service()
    repo.get_by_email = AsyncMock(return_value=None)
    saved_user = _make_user(email="upper@example.com")
    repo.save = AsyncMock(return_value=saved_user)

    await svc.register("UPPER@Example.COM", "Password1", "User")

    saved: User = repo.save.call_args[0][0]
    assert saved.email == "upper@example.com"


# ── Login ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success():
    svc, repo, _ = _make_service()
    hashed = AuthService.hash_password("Correct1")
    user = _make_user(password_hash=hashed)
    repo.get_by_email = AsyncMock(return_value=user)

    result = await svc.login("arun@example.com", "Correct1")
    assert result is user


@pytest.mark.asyncio
async def test_login_wrong_password():
    svc, repo, _ = _make_service()
    hashed = AuthService.hash_password("Correct1")
    user = _make_user(password_hash=hashed)
    repo.get_by_email = AsyncMock(return_value=user)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await svc.login("arun@example.com", "Wrong1")


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """Must return same error as wrong password — prevents user enumeration."""
    svc, repo, _ = _make_service()
    repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await svc.login("ghost@example.com", "Anything1")


@pytest.mark.asyncio
async def test_login_inactive_user_rejected():
    svc, repo, _ = _make_service()
    hashed = AuthService.hash_password("Password1")
    user = _make_user(password_hash=hashed, is_active=False)
    repo.get_by_email = AsyncMock(return_value=user)

    with pytest.raises(AuthenticationError):
        await svc.login("arun@example.com", "Password1")


# ── Google OAuth ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_google_user_creates_new():
    svc, repo, _ = _make_service()
    repo.get_by_google_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    new_user = _make_user(google_id="gid123")
    repo.save = AsyncMock(return_value=new_user)

    google_info = {
        "id": "gid123",
        "email": "arun@gmail.com",
        "name": "Arun Kumar",
        "picture": "https://example.com/pic.jpg",
    }
    user = await svc.get_or_create_google_user(google_info)

    repo.save.assert_awaited_once()
    assert user is new_user


@pytest.mark.asyncio
async def test_get_or_create_google_user_updates_existing():
    svc, repo, _ = _make_service()
    existing = _make_user(google_id="gid123")
    repo.get_by_google_id = AsyncMock(return_value=existing)
    repo.save = AsyncMock(return_value=existing)

    await svc.get_or_create_google_user({
        "id": "gid123",
        "email": "arun@gmail.com",
        "name": "Arun",
        "picture": "https://example.com/new.jpg",
    })

    assert existing.avatar_url == "https://example.com/new.jpg"
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_google_user_no_email_raises():
    svc, repo, _ = _make_service()

    with pytest.raises(AuthenticationError, match="email"):
        await svc.get_or_create_google_user({"id": "gid123", "name": "No Email"})


# ── Token issuance ────────────────────────────────────────────────────────

def test_issue_tokens_returns_non_empty_strings():
    svc, _, _ = _make_service()
    user = _make_user()
    access, refresh = svc.issue_tokens(user)
    assert isinstance(access, str) and len(access) > 20
    assert isinstance(refresh, str) and len(refresh) > 20
    assert access != refresh


# ── Platform token management ─────────────────────────────────────────────

def test_store_and_retrieve_platform_token():
    svc, _, _ = _make_service()
    user = _make_user(encrypted_platform_tokens={}, connected_platforms=[])

    svc.store_platform_token(user, "instagram", {"access_token": "tok123", "user_id": "u1"})
    result = svc.get_platform_token(user, "instagram")

    assert result == {"access_token": "tok123", "user_id": "u1"}
    assert "instagram" in user.connected_platforms


def test_remove_platform_token():
    svc, _, _ = _make_service()
    user = _make_user(encrypted_platform_tokens={}, connected_platforms=[])
    svc.store_platform_token(user, "instagram", {"access_token": "tok"})
    svc.remove_platform_token(user, "instagram")

    assert svc.get_platform_token(user, "instagram") is None
    assert "instagram" not in user.connected_platforms


def test_get_platform_token_missing_returns_none():
    svc, _, _ = _make_service()
    user = _make_user(encrypted_platform_tokens={}, connected_platforms=[])
    assert svc.get_platform_token(user, "youtube") is None