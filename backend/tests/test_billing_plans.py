"""Tests for the billing plans registry and quota enforcement."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.billing import entitlements
from app.services.billing.plans import (
    Plan,
    plan_for_price,
    known_price_ids,
    tier_for_price,
)


def test_plan_for_price_known_id():
    # The settings provide deterministic env-default ids during tests.
    plan = plan_for_price("price_pro_monthly")
    assert plan is not None
    assert plan.tier == "pro"
    assert plan.interval == "month"


def test_plan_for_price_unknown_returns_none():
    assert plan_for_price("price_does_not_exist") is None


def test_tier_for_price_unknown_falls_back_to_free():
    assert tier_for_price(None) == "free"
    assert tier_for_price("garbage") == "free"


def test_known_price_ids_covers_four_plans():
    ids = list(known_price_ids())
    assert len(ids) == 4
    assert all(isinstance(i, str) and i for i in ids)


def test_business_yearly_tier():
    plan = plan_for_price("price_business_yearly")
    assert plan and plan.tier == "business" and plan.interval == "year"


# ─── Quota enforcement ────────────────────────────────────────────────────


def _workspace(tier: str = "free"):
    return SimpleNamespace(id="ws-1", subscription_tier=tier)


@pytest.mark.asyncio
async def test_check_post_quota_within_limit():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=5)))
    allowed, used, cap = await entitlements.check_post_quota(db, _workspace("free"))
    assert allowed is True
    assert used == 5
    assert cap == 30


@pytest.mark.asyncio
async def test_enforce_post_quota_blocks_when_over_cap():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=30)))
    with pytest.raises(HTTPException) as excinfo:
        await entitlements.enforce_post_quota(db, _workspace("free"))
    assert excinfo.value.status_code == 402


@pytest.mark.asyncio
async def test_enforce_platform_quota_blocks_when_at_cap():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=3)))
    with pytest.raises(HTTPException) as excinfo:
        await entitlements.enforce_platform_quota(db, _workspace("free"))
    assert excinfo.value.status_code == 402


@pytest.mark.asyncio
async def test_pro_tier_has_higher_caps():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=100)))
    allowed, used, cap = await entitlements.check_post_quota(db, _workspace("pro"))
    assert allowed is True
    assert cap == 300
