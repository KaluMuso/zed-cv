#!/usr/bin/env python3
"""Retroactive canonicalization of user_skills + job_skills.

Phase 2 Initiative #1 post-merge step. After migration 024 + 025 ship
and skill embeddings are populated, the resolver can detect duplicates
that existed before the canonical_of trigger landed (e.g., a job tagged
with both "postgres" and "postgresql" as separate skill rows).

For each row in user_skills / job_skills:
  1. Look up the skill name.
  2. Re-run that name through resolve_skill_id — gets the canonical id.
  3. If canonical_id != current skill_id, point the junction row at the
     canonical id. The migration 025 BEFORE-UPDATE trigger will also
     walk canonical_of on the way in (idempotent).
  4. Handle PK conflicts: if the canonical (user_id, skill_id) row
     already exists, drop the duplicate row instead of erroring.

Reuses the production resolver code path so live uploads and this
backfill produce identical skill-id assignments. That's the entire
reason we don't do this in SQL — the resolver needs Python (embedding
HTTP call).

Run from the repo root:

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GEMINI_API_KEY=... \\
        python scripts/backfill_canonicalize_job_skills.py

`--dry-run` reports what would change without writing anything.
`--table` lets you backfill just one of user_skills / job_skills.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

# See note in backfill_skill_embeddings.py — Pydantic Settings demands
# these even though the backfill path doesn't use them.
os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_canonicalize_job_skills")


# (table_name, parent_column) — the resolver applies to both junction
# tables. job_skills's parent is `job_id`; user_skills's is `user_id`.
TABLES: list[tuple[str, str]] = [
    ("user_skills", "user_id"),
    ("job_skills", "job_id"),
]


async def _canonicalize_table(
    supabase: Any,
    resolver,  # callable: async def(name, supabase, cache) -> Optional[str]
    table: str,
    parent_col: str,
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Walk one junction table; return {rewritten, deleted, unchanged}."""

    # Fetch all rows + the joined skill name in one round trip. PostgREST
    # embeds make this trivially expressible.
    res = (
        supabase.table(table)
        .select(f"{parent_col}, skill_id, skills(name)")
        .execute()
    )
    rows = res.data or []
    log.info("[%s] scanning %d row(s)", table, len(rows))

    cache: dict[str, str] = {}
    seen_canonical: set[tuple[str, str]] = set()
    rewritten = 0
    deleted = 0
    unchanged = 0

    for row in rows:
        parent_id = row.get(parent_col)
        current_id = row.get("skill_id")
        skill_obj = row.get("skills") or {}
        name = skill_obj.get("name") if isinstance(skill_obj, dict) else None
        if not parent_id or not current_id or not name:
            unchanged += 1
            continue

        canonical = await resolver(name, supabase=supabase, cache=cache)
        if not canonical or canonical == current_id:
            # The trigger in migration 025 will already keep it canonical;
            # nothing to do. Even better: same name -> same id means the
            # resolver agrees with the existing row.
            seen_canonical.add((parent_id, current_id))
            unchanged += 1
            continue

        key = (parent_id, canonical)
        if key in seen_canonical:
            # The canonical row already exists for this parent. Drop the
            # duplicate non-canonical row.
            if dry_run:
                log.info(
                    "[%s] would DELETE %s=%s skill_id=%s (canonical %s "
                    "already present)",
                    table, parent_col, parent_id, current_id, canonical,
                )
            else:
                supabase.table(table).delete().eq(parent_col, parent_id).eq(
                    "skill_id", current_id
                ).execute()
            deleted += 1
            continue

        # No canonical row yet for this parent; rewrite the existing
        # row's skill_id. The migration 025 trigger normalizes
        # canonical_of on the way in, but we set it to the already-
        # canonical id anyway to keep behaviour deterministic.
        if dry_run:
            log.info(
                "[%s] would UPDATE %s=%s skill_id %s -> %s (name=%s)",
                table, parent_col, parent_id, current_id, canonical, name,
            )
        else:
            try:
                supabase.table(table).update({"skill_id": canonical}).eq(
                    parent_col, parent_id
                ).eq("skill_id", current_id).execute()
            except Exception as exc:
                # On the rare race where the canonical row landed between
                # our SELECT and UPDATE, fall through to DELETE — the
                # canonical row already represents this skill for the
                # parent.
                log.warning(
                    "[%s] update %s=%s skill %s->%s failed (%s); "
                    "falling back to delete",
                    table, parent_col, parent_id, current_id, canonical, exc,
                )
                supabase.table(table).delete().eq(parent_col, parent_id).eq(
                    "skill_id", current_id
                ).execute()
                deleted += 1
                continue
        seen_canonical.add(key)
        rewritten += 1

    return {"rewritten": rewritten, "deleted": deleted, "unchanged": unchanged}


async def _run(
    *,
    dry_run: bool,
    only_table: str | None,
) -> int:
    from supabase import create_client

    from app.services.skill_resolver import resolve_skill_id

    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        log.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) "
            "must be set in the environment."
        )
        return 2

    supabase = create_client(url, key)

    overall = {"rewritten": 0, "deleted": 0, "unchanged": 0}
    for table, parent_col in TABLES:
        if only_table and only_table != table:
            continue
        result = await _canonicalize_table(
            supabase,
            resolve_skill_id,
            table,
            parent_col,
            dry_run=dry_run,
        )
        log.info(
            "[%s] rewritten=%d deleted=%d unchanged=%d",
            table, result["rewritten"], result["deleted"], result["unchanged"],
        )
        for k in overall:
            overall[k] += result[k]

    log.info(
        "Done. total rewritten=%d deleted=%d unchanged=%d (dry_run=%s)",
        overall["rewritten"], overall["deleted"], overall["unchanged"], dry_run,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    parser.add_argument(
        "--table",
        choices=["user_skills", "job_skills"],
        default=None,
        help="Backfill only one table (default: both).",
    )
    args = parser.parse_args()
    return asyncio.run(_run(dry_run=args.dry_run, only_table=args.table))


if __name__ == "__main__":
    sys.exit(main())
