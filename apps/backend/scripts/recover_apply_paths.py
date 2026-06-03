#!/usr/bin/env python3
"""Recover apply paths for jobs deactivated pending deep-enrich.

Run from apps/backend:
  python -m scripts.recover_apply_paths --dry-run
  python -m scripts.recover_apply_paths --apply --batch=20

Schedule nightly at 02:00 UTC via n8n (documented in PR; workflow not in repo).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.deep_enrich import enrich_job_deep  # noqa: E402
from app.services.job_quality import (  # noqa: E402
    EMAIL_RE,
    ZM_PHONE_RE,
    _apply_url_is_real,
    has_valid_apply_path,
)
from supabase import create_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("recover_apply_paths")

_JOB_SELECT = (
    "id, title, company, location, description, source_url, apply_url, "
    "apply_email, contact_phone, source, posted_at, closing_date, "
    "created_at, deep_enriched_at, salary_min, salary_max, is_active, "
    "deactivation_reason"
)

_LEGACY_AGGREGATOR_FRAGMENT = (
    "jobwebzambia,gozambiajobs,jobsearchzambia,jobsearchzm,"
    "careersinafrica,everjobs,indeed.com,glassdoor"
)


def _needs_enrich_retry(row: dict[str, Any]) -> bool:
    enriched_at = row.get("deep_enriched_at")
    created_at = row.get("created_at")
    if enriched_at is None:
        return True
    if not created_at:
        return False
    try:
        enriched_dt = datetime.fromisoformat(str(enriched_at).replace("Z", "+00:00"))
        created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        return enriched_dt < created_dt
    except ValueError:
        return True


def _log_outcome(
    supabase: Any,
    *,
    job_id: str,
    outcome: str,
    detail: str | None = None,
    dry_run: bool = False,
) -> None:
    payload = {
        "job_id": job_id,
        "parser_name": "recover_apply_paths",
        "outcome": outcome,
        "detail": (detail or "")[:2000] or None,
        "dry_run": dry_run,
    }
    try:
        supabase.table("apply_url_backfill_log").insert(payload).execute()
    except Exception as exc:
        log.warning("apply_url_backfill_log insert failed for %s: %s", job_id, exc)


def _recovery_outcome(before: dict[str, Any], after: dict[str, Any]) -> str | None:
    """Which channel became valid after enrich, if any."""
    if not has_valid_apply_path(after)[0]:
        return None
    if _apply_url_recovered(before, after):
        return "recovered_apply_url"
    if _email_recovered(before, after):
        return "recovered_apply_email"
    if _phone_recovered(before, after):
        return "recovered_phone"
    return "recovered_apply_url"


def _apply_url_recovered(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return _apply_url_is_real(after.get("apply_url")) and not _apply_url_is_real(
        before.get("apply_url")
    )


def _email_recovered(before: dict[str, Any], after: dict[str, Any]) -> bool:
    after_email = after.get("apply_email")
    before_email = before.get("apply_email")
    if not after_email or not EMAIL_RE.match(str(after_email).strip()):
        return False
    if before_email and EMAIL_RE.match(str(before_email).strip()):
        return False
    return True


def _phone_recovered(before: dict[str, Any], after: dict[str, Any]) -> bool:
    after_phone = after.get("contact_phone")
    before_phone = before.get("contact_phone")
    if not after_phone or not ZM_PHONE_RE.match(str(after_phone).strip()):
        return False
    if before_phone and ZM_PHONE_RE.match(str(before_phone).strip()):
        return False
    return True


def _fetch_pending_enrich(supabase: Any) -> list[dict[str, Any]]:
    result = (
        supabase.table("jobs")
        .select(_JOB_SELECT)
        .eq("is_active", False)
        .eq("deactivation_reason", "no_valid_apply_path_pending_enrich")
        .not_.is_("source_url", "null")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    return [r for r in (result.data or []) if _needs_enrich_retry(r)]


def _fetch_legacy_active_recoverable_broad(supabase: Any) -> list[dict[str, Any]]:
    """Scan active jobs with source_url; filter in Python for aggregator-only paths."""
    result = (
        supabase.table("jobs")
        .select(_JOB_SELECT)
        .eq("is_active", True)
        .not_.is_("source_url", "null")
        .order("created_at", desc=True)
        .limit(2000)
        .execute()
    )
    out: list[dict[str, Any]] = []
    for row in result.data or []:
        if has_valid_apply_path(row)[0]:
            continue
        apply_url = str(row.get("apply_url") or "").lower()
        if not apply_url:
            continue
        domains = _LEGACY_AGGREGATOR_FRAGMENT.split(",")
        if not any(d in apply_url for d in domains):
            continue
        if _needs_enrich_retry(row):
            out.append(row)
    return out


def load_candidates(supabase: Any) -> list[dict[str, Any]]:
    pending = _fetch_pending_enrich(supabase)
    legacy = _fetch_legacy_active_recoverable_broad(supabase)
    by_id: dict[str, dict[str, Any]] = {}
    for row in pending + legacy:
        by_id[str(row["id"])] = row
    return list(by_id.values())


def _refetch_job(supabase: Any, job_id: str) -> dict[str, Any] | None:
    result = (
        supabase.table("jobs")
        .select(_JOB_SELECT)
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]


async def process_job(
    supabase: Any,
    row: dict[str, Any],
    *,
    dry_run: bool,
) -> str:
    """Returns outcome bucket: recovered | deactivated | fetch_failed."""
    job_id = str(row["id"])
    before = dict(row)

    if dry_run:
        log.info(
            "[dry-run] would deep-enrich %s — %s (%s)",
            job_id,
            row.get("title"),
            row.get("source_url"),
        )
        return "dry_run"

    enrich_outcome = await enrich_job_deep(supabase, row, dry_run=False)
    after = _refetch_job(supabase, job_id) or before

    if enrich_outcome == "failed":
        _log_outcome(
            supabase,
            job_id=job_id,
            outcome="deactivated_fetch_failed",
            detail="deep_enrich fetch or LLM failed",
        )
        supabase.table("jobs").update(
            {
                "is_active": False,
                "deactivation_reason": "no_valid_apply_path_after_enrich",
            }
        ).eq("id", job_id).execute()
        return "fetch_failed"

    if has_valid_apply_path(after)[0]:
        recovery = _recovery_outcome(before, after) or "recovered_apply_url"
        _log_outcome(supabase, job_id=job_id, outcome=recovery, detail=enrich_outcome)
        supabase.table("jobs").update(
            {
                "is_active": True,
                "deactivation_reason": None,
                "apply_url": after.get("apply_url"),
                "apply_email": after.get("apply_email"),
                "contact_phone": after.get("contact_phone"),
            }
        ).eq("id", job_id).execute()
        return "recovered"

    _log_outcome(
        supabase,
        job_id=job_id,
        outcome="deactivated_after_enrich_fail",
        detail=enrich_outcome,
    )
    supabase.table("jobs").update(
        {
            "is_active": False,
            "deactivation_reason": "no_valid_apply_path_after_enrich",
        }
    ).eq("id", job_id).execute()
    return "deactivated"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Recover apply paths via deep-enrich")
    parser.add_argument("--dry-run", action="store_true", help="Log only (default)")
    parser.add_argument("--apply", action="store_true", help="Write changes to DB")
    parser.add_argument("--batch", type=int, default=20, help="Max jobs per run")
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run and args.apply:
        dry_run = False

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    candidates = load_candidates(supabase)
    to_process = candidates[: args.batch]

    stats = {"checked": 0, "recovered": 0, "deactivated": 0, "fetch_failed": 0}
    for row in to_process:
        stats["checked"] += 1
        bucket = await process_job(supabase, row, dry_run=dry_run)
        if bucket == "dry_run":
            continue
        if bucket == "recovered":
            stats["recovered"] += 1
        elif bucket == "fetch_failed":
            stats["fetch_failed"] += 1
        elif bucket == "deactivated":
            stats["deactivated"] += 1

    log.info("Summary (dry_run=%s): %s", dry_run, stats)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
