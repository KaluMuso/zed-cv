"""Outbound notification orchestration (web push for high matches)."""
from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.services.web_push import HIGH_MATCH_PUSH_THRESHOLD, send_high_match_push

logger = logging.getLogger(__name__)


async def notify_high_match_web_pushes(
    user_id: str,
    job_ids: list[str],
    supabase: Client,
    *,
    min_score: float = HIGH_MATCH_PUSH_THRESHOLD,
) -> int:
    """After match crediting, push for newly credited rows at or above min_score."""
    unique_ids = list(dict.fromkeys(jid for jid in job_ids if jid))
    if not unique_ids:
        return 0

    result = (
        supabase.table("matches")
        .select("id, job_id, score, credited_at, jobs(title)")
        .eq("user_id", user_id)
        .in_("job_id", unique_ids)
        .gte("score", min_score)
        .not_.is_("credited_at", "null")
        .execute()
    )
    sent = 0
    for row in result.data or []:
        if not isinstance(row, dict):
            continue
        match_id = row.get("id")
        score = float(row.get("score") or 0)
        if not match_id or score < min_score:
            continue
        nested = row.get("jobs") if isinstance(row.get("jobs"), dict) else {}
        title = nested.get("title") or "New role"
        try:
            sent += await send_high_match_push(
                user_id,
                str(match_id),
                str(title),
                score,
                supabase,
            )
        except Exception:
            logger.warning(
                "high-match web push failed user=%s match=%s",
                user_id,
                match_id,
                exc_info=True,
            )
    return sent
