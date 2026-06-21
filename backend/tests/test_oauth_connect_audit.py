"""Credential-connect helper: account upsert + token encryption + audit trail."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.v1.oauth import _upsert_credential_account
from app.domains.control.models import AuditLog, SocialAccount


@pytest.mark.asyncio
async def test_connect_creates_encrypted_account_and_audit(db_session, test_workspace):
    account = await _upsert_credential_account(
        db_session,
        workspace_id=test_workspace.id,
        platform="mastodon",
        platform_user_id="acct-123",
        platform_username="alice",
        display_name="Alice",
        base_url="https://mastodon.example",
        access_token="super-secret-token-xyz",
        scope="write:statuses",
        actor_id=str(test_workspace.owner_id),
    )

    assert account.platform == "mastodon"
    assert account.platform_user_id == "acct-123"
    assert account.platform_url == "https://mastodon.example"
    # Token must be stored encrypted, never as plaintext.
    assert account.encrypted_access_token
    assert account.encrypted_access_token != "super-secret-token-xyz"
    assert "super-secret-token-xyz" not in account.encrypted_access_token

    # An append-only audit entry must record the connection.
    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.workspace_id == test_workspace.id,
                AuditLog.action_type == "social_account.connected",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].resource_id == str(account.id)
    assert rows[0].actor_id == str(test_workspace.owner_id)
    # The plaintext token must NOT leak into the audit summary.
    assert "super-secret-token-xyz" not in str(rows[0].after_summary)


@pytest.mark.asyncio
async def test_connect_is_idempotent_per_platform_user(db_session, test_workspace):
    common = dict(
        workspace_id=test_workspace.id,
        platform="bluesky",
        platform_user_id="did:plc:abc",
        platform_username="alice.bsky.social",
        display_name="Alice",
        base_url="https://bsky.social",
        scope="post",
        actor_id=str(test_workspace.owner_id),
    )
    a1 = await _upsert_credential_account(db_session, access_token="pw-1", **common)
    a2 = await _upsert_credential_account(db_session, access_token="pw-2", **common)

    assert a1.id == a2.id  # same (workspace, platform, platform_user_id) -> updated, not duplicated

    accounts = (
        await db_session.execute(
            select(SocialAccount).where(
                SocialAccount.workspace_id == test_workspace.id,
                SocialAccount.platform == "bluesky",
            )
        )
    ).scalars().all()
    assert len(accounts) == 1
