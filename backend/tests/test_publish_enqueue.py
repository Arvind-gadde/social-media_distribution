"""publish/schedule must enqueue PublishJobs for connected accounts.

Regression guard for the bug where publish_content only flipped project status
and never fed the Celery publish pipeline.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.api.v1.content import _enqueue_publish_jobs
from app.domains.control.models import SocialAccount, TokenStatus
from app.domains.execution.models import (
    ContentProject,
    ContentVariant,
    ProjectStatus,
    PublishJob,
    PublishStatus,
)


async def _make_project_with_variant(db, ws_id, platform: str):
    project = ContentProject(
        workspace_id=ws_id,
        title="t",
        content_type="post",
        status=ProjectStatus.DRAFT,
        target_platforms=[platform],
    )
    db.add(project)
    await db.flush()
    variant = ContentVariant(
        workspace_id=ws_id,
        project_id=project.id,
        target_platform=platform,
        caption="hello",
    )
    db.add(variant)
    await db.flush()
    return project, variant


@pytest.mark.asyncio
async def test_enqueue_creates_job_for_connected_account(db_session, test_workspace):
    ws = test_workspace
    db_session.add(
        SocialAccount(
            workspace_id=ws.id,
            platform="mastodon",
            platform_user_id="u1",
            platform_username="u",
            encrypted_access_token="enc",
            is_active=True,
            token_status=TokenStatus.VALID,
        )
    )
    await db_session.flush()
    project, variant = await _make_project_with_variant(db_session, ws.id, "mastodon")

    n = await _enqueue_publish_jobs(db_session, project, [variant], datetime.now(timezone.utc))
    assert n == 1

    jobs = (
        await db_session.execute(select(PublishJob).where(PublishJob.workspace_id == ws.id))
    ).scalars().all()
    assert len(jobs) == 1
    assert jobs[0].target_platform == "mastodon"
    assert jobs[0].status == PublishStatus.QUEUED
    assert jobs[0].content_variant_id == variant.id

    # Idempotent: a second enqueue must not duplicate the in-flight job.
    n2 = await _enqueue_publish_jobs(db_session, project, [variant], datetime.now(timezone.utc))
    assert n2 == 0


@pytest.mark.asyncio
async def test_enqueue_skips_platform_without_account(db_session, test_workspace):
    ws = test_workspace
    project, variant = await _make_project_with_variant(db_session, ws.id, "bluesky")
    n = await _enqueue_publish_jobs(db_session, project, [variant], datetime.now(timezone.utc))
    assert n == 0  # no connected bluesky account -> nothing enqueued


@pytest.mark.asyncio
async def test_enqueue_skips_inactive_or_invalid_token_account(db_session, test_workspace):
    ws = test_workspace
    db_session.add(
        SocialAccount(
            workspace_id=ws.id,
            platform="mastodon",
            platform_user_id="u2",
            encrypted_access_token="enc",
            is_active=False,  # disconnected
            token_status=TokenStatus.VALID,
        )
    )
    await db_session.flush()
    project, variant = await _make_project_with_variant(db_session, ws.id, "mastodon")
    n = await _enqueue_publish_jobs(db_session, project, [variant], datetime.now(timezone.utc))
    assert n == 0
