#!/usr/bin/env python3
"""Seed canonical_skills with the top 100 Zambia-relevant job skills.

Harvests frequency from jobs.requirements and user_skills (via skills.name),
maps through SKILL_ALIASES + display rules, and upserts canonical rows with
optional parent_skill and notes.

Run from the repo root::

    python apps/backend/scripts/seed_canonical_skills.py
    python apps/backend/scripts/seed_canonical_skills.py --dry-run
    python apps/backend/scripts/seed_canonical_skills.py --print-doc

Environment: SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-seed-scripts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("seed_canonical_skills")


def _format_doc_table(rows: list) -> str:
    lines = [
        "| Canonical name | Parent skill | Notes |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        parent = row.parent_skill or ""
        notes = row.notes or ""
        lines.append(f"| {row.name} | {parent} | {notes} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed canonical_skills table.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned rows without inserting.",
    )
    parser.add_argument(
        "--print-doc",
        action="store_true",
        help="Print markdown table of seed rows to stdout.",
    )
    parser.add_argument(
        "--no-curated-fallback",
        action="store_true",
        help="Do not pad with curated Zambia list when DB counts are sparse.",
    )
    args = parser.parse_args()

    from supabase import create_client

    from app.services.canonical_skills_seed import (
        collect_raw_skill_counts,
        curated_fallback_rows,
        rows_from_top_raw,
        seed_canonical_skills,
    )

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        log.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) must be set."
        )
        return 2

    supabase = create_client(url, key)

    if args.print_doc:
        counts = collect_raw_skill_counts(supabase)
        rows = rows_from_top_raw(counts) if counts else []
        if len(rows) < 100:
            seen = {r.name for r in rows}
            for row in curated_fallback_rows():
                if row.name not in seen:
                    rows.append(row)
                    seen.add(row.name)
                if len(rows) >= 100:
                    break
        print(_format_doc_table(rows[:100]))
        return 0

    rows = seed_canonical_skills(
        supabase,
        dry_run=args.dry_run,
        use_curated_fallback=not args.no_curated_fallback,
    )
    log.info(
        "%s %d canonical skill row(s)",
        "Would seed" if args.dry_run else "Seeded",
        len(rows),
    )
    for row in rows[:20]:
        log.info("  %s (parent=%s)", row.name, row.parent_skill)
    if len(rows) > 20:
        log.info("  ... and %d more", len(rows) - 20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
