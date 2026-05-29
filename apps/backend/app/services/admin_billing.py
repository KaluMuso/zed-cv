"""Admin billing observability — Lenco config status and payment aggregates."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.core.config import Settings
from app.services.invoice import invoice_number

WEBHOOK_URL_EXPECTED = "https://api.zedapply.com/api/v1/webhooks/lenco"


def _count_since(
    supabase: Client,
    *,
    table: str,
    status: str | None = None,
    hours: int | None = None,
    extra_filters: dict[str, Any] | None = None,
) -> int:
    query = supabase.table(table).select("id", count="exact")
    if status:
        query = query.eq("status", status)
    if hours is not None:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        query = query.gte("created_at", since)
    if extra_filters:
        for key, value in extra_filters.items():
            if value is not None:
                query = query.eq(key, value)
    result = query.execute()
    return int(result.count or 0)


async def build_billing_health(
    supabase: Client,
    settings: Settings,
) -> dict[str, Any]:
    """Non-secret Lenco/billing snapshot for the admin portal."""
    now = datetime.now(timezone.utc)
    since_24h = (now - timedelta(hours=24)).isoformat()

    pending = _count_since(supabase, table="payments", status="pending")
    failed_24h = (
        supabase.table("payments")
        .select("id", count="exact")
        .eq("status", "failed")
        .gte("created_at", since_24h)
        .execute()
    )
    completed_24h = (
        supabase.table("payments")
        .select("id", count="exact")
        .eq("status", "completed")
        .gte("completed_at", since_24h)
        .execute()
    )
    lenco_completed_24h = (
        supabase.table("payments")
        .select("id", count="exact")
        .eq("status", "completed")
        .eq("provider", "lenco")
        .gte("completed_at", since_24h)
        .execute()
    )

    cancelling = (
        supabase.table("subscriptions")
        .select("user_id", count="exact")
        .neq("tier", "free")
        .eq("status", "active")
        .not_.is_("cancelled_at", "null")
        .execute()
    )

    production_ready = (
        settings.lenco_environment != "production"
        or (
            settings.lenco_verify_signatures
            and bool(settings.lenco_webhook_secret)
            and bool(settings.lenco_api_key)
            and bool(settings.lenco_public_key)
        )
    )

    return {
        "lenco_environment": settings.lenco_environment,
        "lenco_api_url": settings.lenco_api_url,
        "lenco_api_key_set": bool(settings.lenco_api_key),
        "lenco_public_key_set": bool(settings.lenco_public_key),
        "lenco_webhook_secret_set": bool(settings.lenco_webhook_secret),
        "lenco_verify_signatures": settings.lenco_verify_signatures,
        "lenco_production_ready": production_ready,
        "webhook_url_expected": WEBHOOK_URL_EXPECTED,
        "payments_pending": pending,
        "payments_failed_24h": int(failed_24h.count or 0),
        "payments_completed_24h": int(completed_24h.count or 0),
        "lenco_completed_24h": int(lenco_completed_24h.count or 0),
        "subscriptions_cancelling": int(cancelling.count or 0),
        "checked_at": now.isoformat(),
    }


def summarize_webhook_data(raw: Any) -> dict[str, Any] | None:
    """Extract safe webhook fields for admin display."""
    if not isinstance(raw, dict):
        return None
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    return {
        "event": raw.get("event"),
        "reference": data.get("reference") or data.get("companyRef"),
        "lenco_status": data.get("status"),
        "transaction_ref": data.get("transactionRef") or data.get("id"),
        "resolved_tier": raw.get("_resolved_tier"),
        "inexact_amount_match": raw.get("_inexact_amount_match"),
    }
