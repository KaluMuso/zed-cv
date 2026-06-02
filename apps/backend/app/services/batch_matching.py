"""Nightly batch matching and cached refresh helpers."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from app.services.matching import (
    credit_matches_for_cycle,
    match_rpc_limit_for_user,
    run_matching_for_user,
    store_matches,
)

logger = logging.getLogger(__name__)

BATCH_MATCH_LIMIT = 50
BATCH_USER_CHUNK_SIZE = 100
BATCH_PRUNE_DAYS = 7


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def create_batch_run(supabase: Client) -> str:
    """Insert match_batch_runs row; return batch run id."""
    batch_id = str(uuid.uuid4())
    supabase.table("match_batch_runs").insert(
        {"id": batch_id, "started_at": _utc_now().isoformat()}
    ).execute()
    return batch_id


async def finalize_batch_run(
    supabase: Client,
    batch_id: str,
    *,
    users_processed: int,
    matches_created: int,
    error_count: int,
    notes: str | None = None,
) -> None:
    supabase.table("match_batch_runs").update(
        {
            "completed_at": _utc_now().isoformat(),
            "users_processed": users_processed,
            "matches_created": matches_created,
            "error_count": error_count,
            "notes": notes,
        }
    ).eq("id", batch_id).execute()


async def run_on_demand_match_for_user(
    user_id: str,
    cv_id: str,
    supabase: Client,
    *,
    limit: int = BATCH_MATCH_LIMIT,
) -> tuple[str, int]:
    """Live RPC match for one user (CV upload / first-time fallback)."""
    batch_id = str(uuid.uuid4())
    batch_at = _utc_now().isoformat()
    rpc_limit = await match_rpc_limit_for_user(user_id, supabase, limit)
    if rpc_limit <= 0:
        return batch_id, 0
    matches = await run_matching_for_user(user_id, supabase, limit=rpc_limit)
    stored = await store_matches(
        user_id,
        cv_id,
        matches,
        supabase,
        batch_run_id=batch_id,
        batch_run_at=batch_at,
    )
    job_ids = [str(m["job_id"]) for m in matches if m.get("job_id")]
    if job_ids:
        await credit_matches_for_cycle(user_id, job_ids, supabase)
    return batch_id, stored


async def run_batch_match_for_user(
    user_id: str,
    cv_id: str,
    batch_run_id: str,
    batch_run_at: str,
    supabase: Client,
) -> int:
    """Run RPC + persist top matches for one user in a nightly batch."""
    rpc_limit = await match_rpc_limit_for_user(user_id, supabase, BATCH_MATCH_LIMIT)
    if rpc_limit <= 0:
        return 0
    matches = await run_matching_for_user(user_id, supabase, limit=rpc_limit)
    stored = await store_matches(
        user_id,
        cv_id,
        matches,
        supabase,
        batch_run_id=batch_run_id,
        batch_run_at=batch_run_at,
    )
    job_ids = [str(m["job_id"]) for m in matches if m.get("job_id")]
    if job_ids:
        await credit_matches_for_cycle(user_id, job_ids, supabase)
    return stored


async def _primary_cv_id(user_id: str, supabase: Client) -> str | None:
    cv_result = (
        supabase.table("cvs")
        .select("id")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    if not cv_result.data:
        return None
    return str(cv_result.data[0]["id"])


def _fetch_active_user_ids(supabase: Client, offset: int, limit: int) -> list[str]:
    result = (
        supabase.table("users")
        .select("id")
        .eq("is_active", True)
        .order("id")
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [str(row["id"]) for row in (result.data or []) if row.get("id")]


async def run_nightly_batch_match(
    supabase: Client,
    batch_id: str | None = None,
    *,
    settings: Any | None = None,
) -> dict[str, Any]:
    """Process all active users in chunks; prune matches older than 7 days."""
    if batch_id is None:
        batch_id = await create_batch_run(supabase)
    batch_at = _utc_now().isoformat()
    users_processed = 0
    matches_created = 0
    error_count = 0
    offset = 0

    while True:
        user_ids = _fetch_active_user_ids(supabase, offset, BATCH_USER_CHUNK_SIZE)
        if not user_ids:
            break
        offset += BATCH_USER_CHUNK_SIZE
        logger.info(
            "batch_match chunk offset=%s size=%s batch_id=%s",
            offset - BATCH_USER_CHUNK_SIZE,
            len(user_ids),
            batch_id,
        )
        for user_id in user_ids:
            try:
                cv_id = await _primary_cv_id(user_id, supabase)
                if not cv_id:
                    continue
                stored = await run_batch_match_for_user(
                    user_id, cv_id, batch_id, batch_at, supabase
                )
                users_processed += 1
                matches_created += stored
            except Exception:
                error_count += 1
                logger.exception(
                    "batch_match failed user=%s batch_id=%s", user_id, batch_id
                )

    pruned = await prune_old_batch_matches(supabase, days=BATCH_PRUNE_DAYS)
    notes = f"pruned_rows={pruned}" if pruned else None
    await finalize_batch_run(
        supabase,
        batch_id,
        users_processed=users_processed,
        matches_created=matches_created,
        error_count=error_count,
        notes=notes,
    )
    if error_count > 0 and settings is not None:
        from app.services.admin_alerts import send_admin_whatsapp

        msg = (
            f"ZedApply nightly batch-match finished with {error_count} error(s). "
            f"users={users_processed} matches={matches_created} batch={batch_id}"
        )
        try:
            await send_admin_whatsapp(msg, settings)
        except Exception:
            logger.warning("batch-match alert WhatsApp failed", exc_info=True)
    return {
        "batch_run_id": batch_id,
        "users_processed": users_processed,
        "matches_created": matches_created,
        "error_count": error_count,
        "pruned_rows": pruned,
    }


async def prune_old_batch_matches(supabase: Client, *, days: int = BATCH_PRUNE_DAYS) -> int:
    """Delete batch-tagged match rows older than ``days`` (analytics window)."""
    cutoff = (_utc_now() - timedelta(days=days)).isoformat()
    result = (
        supabase.table("matches")
        .delete()
        .not_.is_("batch_run_id", "null")
        .lt("batch_run_at", cutoff)
        .execute()
    )
    if result.data is None:
        return 0
    return len(result.data)


async def get_latest_batch_for_user(
    user_id: str, supabase: Client
) -> tuple[str | None, str | None]:
    """Return (batch_run_id, batch_run_at) for the user's newest batch."""
    result = (
        supabase.table("matches")
        .select("batch_run_id, batch_run_at")
        .eq("user_id", user_id)
        .not_.is_("batch_run_id", "null")
        .order("batch_run_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None, None
    row = result.data[0]
    return row.get("batch_run_id"), row.get("batch_run_at")


async def user_has_batch_matches(user_id: str, supabase: Client) -> bool:
    batch_id, _ = await get_latest_batch_for_user(user_id, supabase)
    return batch_id is not None


async def fetch_cached_batch_matches(
    user_id: str,
    supabase: Client,
    *,
    batch_run_id: str,
    min_score: float = 50.0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    from app.services.matching import fetch_delivered_match_rows

    return await fetch_delivered_match_rows(
        user_id,
        supabase,
        min_score=min_score,
        limit=limit,
        batch_run_id=batch_run_id,
    )
