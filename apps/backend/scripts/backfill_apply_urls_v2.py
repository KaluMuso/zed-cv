#!/usr/bin/env python3
"""Backfill employer apply_url using v2 per-aggregator parsers.

Dry-run by default. With --apply, updates jobs and writes apply_url_backfill_log.

Run from repo root::

    cd apps/backend && python scripts/backfill_apply_urls_v2.py
    cd apps/backend && python scripts/backfill_apply_urls_v2.py --apply

Requires SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

from supabase import create_client  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.deep_link_parsers import (  # noqa: E402
    CONFIDENCE_UPDATE_THRESHOLD,
    PARSER_CONFIDENCE_THRESHOLDS,
    parser_name_for_url,
    should_update_apply_url,
)
from app.services.job_apply_url_heuristics import (  # noqa: E402
    is_aggregator,
    resolve_apply_contacts_from_aggregator_url,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_apply_urls_v2")

PROGRESS_PATH = Path("/tmp/zedcv_apply_url_backfill_v2_progress.json")
THROTTLE_SECONDS = 1.0


def _domain(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def _load_progress() -> dict[str, str]:
    if not PROGRESS_PATH.exists():
        return {}
    try:
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read progress file %s: %s", PROGRESS_PATH, exc)
    return {}


def _save_progress(progress: dict[str, str]) -> None:
    PROGRESS_PATH.write_text(
        json.dumps(progress, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def count_aggregator_apply_urls(supabase: Any) -> int:
    res = (
        supabase.table("jobs")
        .select("id, apply_url")
        .eq("is_active", True)
        .execute()
    )
    return sum(
        1
        for row in (res.data or [])
        if is_aggregator(str(row.get("apply_url") or ""))
    )


def _load_candidates(supabase: Any) -> list[dict[str, Any]]:
    res = (
        supabase.table("jobs")
        .select("id, title, apply_url, apply_email, contact_phone")
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    return [
        row
        for row in (res.data or [])
        if is_aggregator(str(row.get("apply_url") or ""))
    ]


def _log_row(
    supabase: Any,
    *,
    job_id: str,
    old_url: str,
    new_url: str | None,
    apply_email: str | None,
    contact_phone: str | None,
    parser_name: str | None,
    parser_confidence: float,
    dry_run: bool,
) -> None:
    payload = {
        "job_id": job_id,
        "old_apply_url": old_url,
        "new_apply_url": new_url,
        "apply_email": apply_email,
        "contact_phone": contact_phone,
        "parser_name": parser_name,
        "parser_confidence": parser_confidence,
        "dry_run": dry_run,
    }
    try:
        supabase.table("apply_url_backfill_log").insert(payload).execute()
    except Exception as exc:
        log.warning("apply_url_backfill_log insert failed for %s: %s", job_id, exc)


async def _resolve_v2(apply_url: str) -> tuple[Any, str]:
    """Parse with v2 registry + redirect follow (same as ingest path)."""
    from app.services.job_apply_url_heuristics import ApplyContacts

    contacts = await resolve_apply_contacts_from_aggregator_url(apply_url)
    return contacts, contacts.parser_name or parser_name_for_url(apply_url)


async def run_backfill(
    *, apply: bool, limit: int | None, reset_progress: bool = False
) -> int:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        log.error("SUPABASE_URL and SUPABASE_KEY must be set")
        return 1

    supabase = create_client(settings.supabase_url, settings.supabase_key)
    if apply and reset_progress and PROGRESS_PATH.exists():
        PROGRESS_PATH.unlink()
        log.info("Cleared progress file %s", PROGRESS_PATH)
    progress = _load_progress() if apply else {}

    before = count_aggregator_apply_urls(supabase)
    print(f"aggregator_apply_urls_before: {before}")
    print(f"confidence_update_threshold: {CONFIDENCE_UPDATE_THRESHOLD}")
    print(f"parser_thresholds: {json.dumps(PARSER_CONFIDENCE_THRESHOLDS)}")

    candidates = _load_candidates(supabase)
    if apply:
        candidates = [
            row for row in candidates if progress.get(str(row["id"])) != "done"
        ]
    if limit is not None:
        candidates = candidates[:limit]

    by_domain: dict[str, int] = defaultdict(int)
    fixed_by_domain: dict[str, int] = defaultdict(int)
    stats: dict[str, int] = defaultdict(int)
    proposed: list[tuple[str, str, str, float, str]] = []
    still_aggregator: list[tuple[str, str, str]] = []

    for row in candidates:
        job_id = str(row["id"])
        title = str(row.get("title") or "")
        original = str(row.get("apply_url") or "")
        domain = _domain(original)
        by_domain[domain] += 1

        contacts, parser_name = await _resolve_v2(original)
        await asyncio.sleep(THROTTLE_SECONDS)

        from app.services.deep_link_parsers import ApplyContact

        contact = ApplyContact(
            apply_url=contacts.apply_url,
            apply_email=contacts.apply_email,
            contact_phone=contacts.contact_phone,
            parser_confidence=contacts.parser_confidence,
            parser_name=parser_name,
        )

        will_update = should_update_apply_url(contact, original_url=original)
        if will_update:
            stats["proposed_update"] += 1
            fixed_by_domain[domain] += 1
            if len(proposed) < 10:
                proposed.append(
                    (
                        job_id,
                        original,
                        contact.apply_url or "",
                        contact.parser_confidence,
                        parser_name,
                    )
                )
        elif is_aggregator(original):
            stats["still_aggregator"] += 1
            if len(still_aggregator) < 25:
                still_aggregator.append((job_id, title, original))
        else:
            stats["unchanged"] += 1

        _log_row(
            supabase,
            job_id=job_id,
            old_url=original,
            new_url=contact.apply_url if will_update else None,
            apply_email=contact.apply_email,
            contact_phone=contact.contact_phone,
            parser_name=parser_name,
            parser_confidence=contact.parser_confidence,
            dry_run=not apply,
        )

        if apply and will_update and contact.apply_url:
            patch: dict[str, Any] = {
                "apply_url": contact.apply_url,
                "apply_source": "enriched",
            }
            if contact.apply_email and not row.get("apply_email"):
                patch["apply_email"] = contact.apply_email
            if contact.contact_phone and not row.get("contact_phone"):
                patch["contact_phone"] = contact.contact_phone
            supabase.table("jobs").update(patch).eq("id", job_id).execute()
            progress[job_id] = "done"
            _save_progress(progress)
            stats["applied"] += 1

    after = count_aggregator_apply_urls(supabase) if apply else before
    proposed_n = stats.get("proposed_update", 0)
    still_n = stats.get("still_aggregator", 0)
    projected_remaining = before - proposed_n if not apply else after

    print(f"aggregator_apply_urls_after: {after}")
    print(f"delta: {before - after}")
    print("per_domain_jobs:")
    for domain, count in sorted(by_domain.items()):
        fixed = fixed_by_domain.get(domain, 0)
        print(f"  {domain}: total={count} proposed_fix={fixed}")
    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")
    if proposed:
        print("proposed_changes_sample:")
        for job_id, old_u, new_u, conf, pname in proposed:
            print(f"  {job_id[:8]} | {pname} conf={conf:.2f}")
            print(f"    {old_u}")
            print(f"    -> {new_u}")
    if still_aggregator:
        print("remaining_aggregator_sample (manual queue):")
        for job_id, title, url in still_aggregator[:15]:
            print(f"  {job_id} | {title[:50]} | {url}")

    print("--- dry_run_summary ---")
    print(f"candidates_processed: {len(candidates)}")
    print(f"proposed_update: {proposed_n}")
    print(f"still_aggregator: {still_n}")
    print(f"projected_aggregator_remaining: {projected_remaining}")
    log.info(
        "backfill complete apply=%s before=%s after=%s proposed=%s still=%s",
        apply,
        before,
        after,
        proposed_n,
        still_n,
    )

    if not apply:
        print("Dry-run: pass --apply to persist updates and audit log.")
        print(
            "Human approval gate (see docs/APPLY_URL_BACKFILL_V2_RUNBOOK.md §3): "
            "review all proposed_changes_sample URLs; projected remaining must be < 20; "
            "ops owner must reply Y before --apply."
        )
        if projected_remaining > 20:
            log.warning(
                "projected_aggregator_remaining=%s exceeds target < 20",
                projected_remaining,
            )
    elif after >= 20:
        log.warning(
            "aggregator_apply_urls_after=%s — manual queue may still be large",
            after,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write resolved URLs and audit log (default dry-run)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max jobs this run")
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Ignore /tmp v2 progress file when applying",
    )
    args = parser.parse_args()
    if args.apply:
        log.info("APPLY mode — jobs + apply_url_backfill_log may be updated")
    return asyncio.run(
        run_backfill(
            apply=args.apply,
            limit=args.limit,
            reset_progress=args.reset_progress,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
