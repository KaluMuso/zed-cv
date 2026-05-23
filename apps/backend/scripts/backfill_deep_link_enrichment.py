#!/usr/bin/env python3
"""Backfill apply_url/apply_email from jobs.source_url via deep_link_enricher.

Usage (from apps/backend with .env loaded):
  python3 scripts/backfill_deep_link_enrichment.py [--limit N] [--dry-run]
  python3 scripts/backfill_deep_link_enrichment.py --force-reparse [--limit N]

Rate-limits to 2 seconds between HTTP fetches (respectful scraping).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

# Allow `python3 scripts/...` from apps/backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.services.deep_link_enricher import (  # noqa: E402
    enrich_job_row,
    job_needs_enrichment,
    reparse_job_row,
)
from supabase import create_client  # noqa: E402


async def run(*, limit: int | None, dry_run: bool, force_reparse: bool) -> None:
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    if force_reparse:
        query = (
            supabase.table("jobs")
            .select(
                "id, source_url, apply_url, apply_email, contact_phone, "
                "enrichment_attempted_at, is_enriched"
            )
            .eq("is_enriched", True)
            .not_.is_("source_url", "null")
            .order("posted_at", desc=True)
        )
    else:
        query = (
            supabase.table("jobs")
            .select("id, source_url, apply_url, apply_email, enrichment_attempted_at")
            .is_("apply_url", "null")
            .is_("apply_email", "null")
            .not_.is_("source_url", "null")
            .order("posted_at", desc=True)
        )
    if limit:
        query = query.limit(limit)

    rows = query.execute().data or []
    if force_reparse:
        candidates = rows
    else:
        candidates = [r for r in rows if job_needs_enrichment(r)]
    print(f"Found {len(candidates)} jobs to process (of {len(rows)} queried)")

    enriched = 0
    for idx, row in enumerate(candidates):
        job_id = row["id"]
        if dry_run:
            print(f"[dry-run] would enrich {job_id} {row.get('source_url')}")
        else:
            if force_reparse:
                ok = await reparse_job_row(supabase, job_id, row, force=True)
            else:
                ok = await enrich_job_row(supabase, job_id, row)
            if ok:
                enriched += 1
                print(f"enriched {job_id}")
            else:
                print(f"no contact found {job_id}")
        if idx < len(candidates) - 1:
            await asyncio.sleep(2.0)

    if not dry_run:
        pct = (enriched / len(candidates) * 100) if candidates else 0
        print(f"Done: {enriched}/{len(candidates)} enriched ({pct:.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force-reparse",
        action="store_true",
        help="Re-run parsers on is_enriched jobs (missed emails on first pass)",
    )
    args = parser.parse_args()
    asyncio.run(
        run(limit=args.limit, dry_run=args.dry_run, force_reparse=args.force_reparse)
    )


if __name__ == "__main__":
    main()
