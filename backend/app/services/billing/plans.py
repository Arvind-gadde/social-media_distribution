"""Plan / Stripe price registry.

Centralizes the mapping between Stripe Price IDs (configured via env) and the
internal plan tier values (``free`` / ``pro`` / ``business``).  Used by the
checkout endpoint, the Stripe webhook handler, and entitlement enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.config import get_settings


@dataclass(frozen=True)
class Plan:
    key: str           # e.g. "pro_monthly"
    tier: str          # internal tier (free|pro|business)
    interval: str      # month|year
    display_name: str
    price_id: str      # Stripe price id


def _build_plans() -> tuple[Plan, ...]:
    s = get_settings()
    plans = (
        Plan("pro_monthly",      "pro",      "month", "Pro Monthly",      s.PRICE_PRO_MONTHLY),
        Plan("pro_yearly",       "pro",      "year",  "Pro Yearly",       s.PRICE_PRO_YEARLY),
        Plan("business_monthly", "business", "month", "Business Monthly", s.PRICE_BUSINESS_MONTHLY),
        Plan("business_yearly",  "business", "year",  "Business Yearly",  s.PRICE_BUSINESS_YEARLY),
    )
    return plans


PLANS: tuple[Plan, ...] = _build_plans()


def plan_for_price(price_id: str) -> Plan | None:
    for p in PLANS:
        if p.price_id == price_id:
            return p
    return None


def tier_for_price(price_id: str | None) -> str:
    """Return the internal tier for a Stripe price id; ``free`` when unknown."""
    if not price_id:
        return "free"
    plan = plan_for_price(price_id)
    return plan.tier if plan else "free"


def known_price_ids() -> Iterable[str]:
    return tuple(p.price_id for p in PLANS)
