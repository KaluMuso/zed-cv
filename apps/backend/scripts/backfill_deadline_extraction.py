#!/usr/bin/env python3
"""Backfill closing_date from descriptions via regex + LLM (Track 4e).

Usage (from apps/backend with .env loaded):
  python3 scripts/backfill_deadline_extraction.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.services.job_deadline_extractor import extract_closing_date_llm  # noqa: E402
from app.services.job_activation import apply_review_state_to_row, compute_review_state  # noqa: E402
from supabase import create_client  # noqa: E402


async def run(*, limit: int | None, dry_run: bool) -> None:
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    query = (
        supabase.table("jobs")
        .select("id, title, company, description, closing_date, apply_url, apply_email")
        .is_("closing_date", "null")
        .order("created_at", desc=True)
    )
    if limit:
        query = query.limit(limit)
    rows = query.execute().data or []
    print(f"Processing {len(rows)} jobs without closing_date")

    updated = 0
    for idx, row in enumerate(rows):
        closing = await extract_closing_date_llm(
            row.get("description") or "",
            row.get("title") or "",
            row.get("company") or "",
        )
        if not closing:
            continue
        patch = {"closing_date": closing.isoformat()}
        review = compute_review_state(
            apply_url=row.get("apply_url"),
            apply_email=row.get("apply_email"),
            closing_date=closing.isoformat(),
        )
        apply_review_state_to_row(patch, review)

        if dry_run:
            print(f"[dry-run] {row['id']}: closing_date={closing}")
        else:
            supabase.table("jobs").update(patch).eq("id", row["id"]).execute()
            updated += 1
        if idx < len(rows) - 1:
            await asyncio.sleep(0.5)

    print(f"Done: {updated} deadlines set (dry_run={dry_run})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
