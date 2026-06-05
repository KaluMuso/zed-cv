#!/usr/bin/env python3
"""Backfill deep-enrich for jobs missing deep_enriched_at.

Run from apps/backend:
  python -m scripts.backfill_deep_enrich --dry-run
  python -m scripts.backfill_deep_enrich --apply --batch=25
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.deep_enrich import (  # noqa: E402
    _needs_deep_enrich,
    _resolve_fetch_url,
    enrich_job_deep,
)
from supabase import create_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backfill_deep_enrich")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill deep-enrich pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Log only (default)")
    parser.add_argument("--apply", action="store_true", help="Write changes to DB")
    parser.add_argument("--batch", type=int, default=25, help="Max jobs per batch")
    parser.add_argument("--age-days", type=int, default=30, help="Reserved for future filter")
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run and args.apply:
        dry_run = False

    del args.age_days  # reserved

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    result = (
        supabase.table("jobs")
        .select(
            "id, title, company, location, description, source_url, apply_url, "
            "apply_email, contact_phone, source, posted_at, closing_date, "
            "created_at, deep_enriched_at, salary_min, salary_max, is_active"
        )
        .eq("is_active", True)
        .is_("deep_enriched_at", "null")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    rows = [r for r in (result.data or []) if _needs_deep_enrich(r)]
    to_process = rows[: args.batch]

    stats = {
        "enriched": 0,
        "split": 0,
        "failed_no_url": 0,
        "failed_fetch": 0,
        "failed": 0,
        "skipped": 0,
    }

    for row in to_process:
        job_id = str(row["id"])
        if not _resolve_fetch_url(row):
            stats["failed_no_url"] += 1
            log.info("[%s] no_url — %s", job_id, row.get("title"))
            if not dry_run:
                from app.services.deep_enrich import _log_enrich

                _log_enrich(
                    supabase,
                    job_id=job_id,
                    outcome="failed_no_url",
                    detail="no_url",
                )
            continue

        if dry_run:
            log.info(
                "[dry-run] would enrich %s — %s (%s)",
                job_id,
                row.get("title"),
                _resolve_fetch_url(row),
            )
            stats["enriched"] += 1
            continue

        result = await enrich_job_deep(supabase, row, dry_run=False)
        if result.outcome == "enriched":
            stats["enriched"] += 1
        elif result.outcome == "split":
            stats["split"] += 1
        elif result.outcome == "skipped":
            stats["skipped"] += 1
        elif result.outcome == "failed" and not _resolve_fetch_url(row):
            stats["failed_no_url"] += 1
        else:
            stats["failed"] += 1
            stats["failed_fetch"] += 1

    log.info("Done (dry_run=%s): %s", dry_run, stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
