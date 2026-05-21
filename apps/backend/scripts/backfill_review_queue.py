#!/usr/bin/env python3
"""Backfill is_review_required / review_reason for existing jobs (Track 4e).

Preserves is_active=true for jobs that already have a working apply path.

Usage (from apps/backend with .env loaded):
  python3 scripts/backfill_review_queue.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.services.job_activation import apply_review_state_to_row, compute_review_state  # noqa: E402
from supabase import create_client  # noqa: E402


def run(*, limit: int | None, dry_run: bool) -> None:
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    query = supabase.table("jobs").select(
        "id, apply_url, apply_email, closing_date, is_active"
    ).order("created_at", desc=True)
    if limit:
        query = query.limit(limit)
    rows = query.execute().data or []

    updated = 0
    for row in rows:
        review = compute_review_state(
            apply_url=row.get("apply_url"),
            apply_email=row.get("apply_email"),
            closing_date=row.get("closing_date"),
        )
        patch: dict = {
            "is_review_required": review.is_review_required,
            "review_reason": review.review_reason,
            "admin_review_reason": review.admin_review_reason,
        }
        if not review.is_active and not row.get("apply_url") and not row.get("apply_email"):
            patch["is_active"] = False
        elif review.is_review_required and row.get("is_active"):
            pass
        elif not review.is_review_required:
            patch["is_active"] = True

        if dry_run:
            print(f"[dry-run] {row['id']}: {patch}")
        else:
            supabase.table("jobs").update(patch).eq("id", row["id"]).execute()
            updated += 1

    print(f"Done: {updated} jobs flagged (dry_run={dry_run})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
