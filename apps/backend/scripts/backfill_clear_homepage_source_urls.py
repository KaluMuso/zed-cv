#!/usr/bin/env python3
"""Clear aggregator homepage values mistakenly stored as jobs.source_url.

Rows with source_url like https://jobwebzambia.com/ cannot be deep-linked or
enriched. This script nulls those URLs and clears enrichment_attempted_at so
deep-link / deep-enrich backfills can retry once listing URLs exist.

Usage (from apps/backend with .env loaded):
  python3 -m scripts.backfill_clear_homepage_source_urls --dry-run
  python3 -m scripts.backfill_clear_homepage_source_urls --apply --limit=500
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

from app.core.config import get_settings  # noqa: E402
from app.services.deep_link_parsers.base import (  # noqa: E402
    is_aggregator_site_root,
    sanitize_listing_source_url,
)
from supabase import create_client  # noqa: E402


def run(*, apply: bool, limit: int) -> None:
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    rows = (
        supabase.table("jobs")
        .select(
            "id, title, source_url, apply_url, enrichment_attempted_at, "
            "is_review_required"
        )
        .not_.is_("source_url", "null")
        .limit(limit)
        .execute()
        .data
        or []
    )

    cleared = 0
    for row in rows:
        source = str(row.get("source_url") or "")
        if not is_aggregator_site_root(source):
            continue
        cleaned_apply = sanitize_listing_source_url(str(row.get("apply_url") or ""))
        patch: dict[str, object] = {
            "source_url": cleaned_apply,
            "enrichment_attempted_at": None,
        }
        if is_aggregator_site_root(str(row.get("apply_url") or "")):
            patch["apply_url"] = None
        cleared += 1
        if apply:
            supabase.table("jobs").update(patch).eq("id", row["id"]).execute()
        else:
            print(
                f"[dry-run] {row['id'][:8]}… {row.get('title', '')!r}: "
                f"source_url {source!r} -> {patch.get('source_url')!r}"
            )

    print(f"Scanned {len(rows)} rows with source_url set")
    print(f"Homepage source_url cleared: {cleared} (apply={apply})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=500, help="Max rows to scan")
    args = parser.parse_args()
    run(apply=args.apply, limit=args.limit)


if __name__ == "__main__":
    main()
