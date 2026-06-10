"""Subscription billing-period activation after successful payment."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def activate_subscription_after_payment(
    supabase: Client,
    *,
    user_id: str,
    payment_id: str,
    new_tier: str,
    subscription_row: dict[str, Any] | None,
    lenco_subscription_ref: Optional[str] = None,
    billing_period_days: int | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    """Apply paid-tier activation via Postgres RPC activate_subscription_after_payment."""
    settings = get_settings()
    existing_end = _parse_dt((subscription_row or {}).get("current_period_end"))
    existing_iso = existing_end.isoformat() if existing_end else None

    rpc_args: dict[str, Any] = {
        "p_user_id": user_id,
        "p_payment_id": payment_id,
        "p_new_tier": new_tier,
        "p_subscription_id": (subscription_row or {}).get("id"),
        "p_lenco_subscription_ref": lenco_subscription_ref,
        "p_period_days": billing_period_days or settings.subscription_period_days,
        "p_existing_period_end": existing_iso,
    }

    result = supabase.rpc("activate_subscription_after_payment", rpc_args).execute()
    payload = result.data
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        payload = {}

    period_start = payload.get("period_start")
    period_end = payload.get("period_end")
    if not period_start or not period_end:
        current = now or datetime.now(timezone.utc)
        period_start = current.isoformat()
        period_end = period_start

    period_iso = {
        "start": str(period_start),
        "end": str(period_end),
    }

    logger.info(
        "Subscription activated: user=%s tier=%s period_end=%s sub_id=%s",
        user_id,
        new_tier,
        period_iso["end"],
        payload.get("subscription_id"),
    )

    try:
        from app.services.referral import reward_referral_on_first_paid_subscription

        reward_referral_on_first_paid_subscription(user_id, new_tier, supabase)
    except Exception:
        logger.warning(
            "referral reward failed for user=%s tier=%s",
            user_id,
            new_tier,
            exc_info=True,
        )

    return period_iso
