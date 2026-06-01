"""Aggregate Bwana chat analytics for admin dashboard."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.schemas.bwana_config import BwanaAnalyticsSummary


def _since_iso(days: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return since.isoformat()


def fetch_bwana_analytics(supabase: Client, *, days: int = 7) -> BwanaAnalyticsSummary:
    since = _since_iso(days)

    events_resp = (
        supabase.table("bwana_event_log")
        .select("source,intent_id,created_at")
        .gte("created_at", since)
        .execute()
    )
    events = events_resp.data or []

    esc_resp = (
        supabase.table("bwana_escalation_log")
        .select("reason,created_at")
        .gte("created_at", since)
        .execute()
    )
    escalations = esc_resp.data or []

    total_messages = len(events)
    total_escalations = len(escalations)
    rate = (
        round(100.0 * total_escalations / total_messages, 1)
        if total_messages > 0
        else 0.0
    )

    by_source: Counter[str] = Counter()
    faq_intents: Counter[str] = Counter()
    for row in events:
        src = str(row.get("source") or "llm")
        by_source[src] += 1
        if src == "faq":
            iid = str(row.get("intent_id") or "unknown")
            faq_intents[iid] += 1

    by_reason: Counter[str] = Counter()
    for row in escalations:
        by_reason[str(row.get("reason") or "unknown")] += 1

    top_faq = [
        {"intent_id": k, "count": v}
        for k, v in faq_intents.most_common(15)
    ]
    return BwanaAnalyticsSummary(
        period_days=days,
        total_messages=total_messages,
        total_escalations=total_escalations,
        escalation_rate_percent=rate,
        messages_by_source=dict(by_source),
        escalations_by_reason=dict(by_reason),
        top_faq_intents=top_faq,
    )
