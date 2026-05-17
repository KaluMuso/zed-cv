#!/usr/bin/env python3
"""One-shot: populate skills.embedding for every row where it's NULL.

Phase 2 Initiative #1 post-merge step 2 (see PR description). Migration
024 adds the column; this script runs once to backfill. Idempotent —
re-running only re-embeds rows still missing the column, so it's safe to
re-run after a partial network failure.

Uses the production embedding pipeline so the resulting vectors live in
the same coordinate space as cvs.embedding / jobs.embedding.

Run from the repo root:

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GEMINI_API_KEY=... \\
        python scripts/backfill_skill_embeddings.py

Defaults are tuned for the ~99 rows currently in `skills`; bump
`--batch-size` if the table grows.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Make `app.*` importable without installing the backend as a package.
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

# Backfill scripts read SUPABASE_SERVICE_KEY directly, but importing
# app.services.embedding pulls in app.core.config.Settings, which
# requires SUPABASE_KEY + JWT_SECRET present in the env even when the
# code path under test only needs GEMINI_API_KEY. Synthesize them so
# the documented env-var set (URL + SERVICE_KEY + GEMINI) is enough.
# This DOES NOT weaken any auth — JWT_SECRET is only used by the auth
# code path, which the backfill never touches.
os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_skill_embeddings")


async def _run(batch_size: int, sleep_between_batches: float) -> int:
    """Returns process exit code (0 on full success, 1 if any row failed)."""
    from supabase import create_client

    from app.services.embedding import generate_embedding

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

    pending = (
        supabase.table("skills")
        .select("id, name")
        .is_("embedding", "null")
        .execute()
    )
    rows = pending.data or []
    if not rows:
        log.info("No skills need embedding backfill. Nothing to do.")
        return 0

    log.info("Backfilling embeddings for %d skill(s)", len(rows))

    success = 0
    failed = 0
    for i, row in enumerate(rows, start=1):
        name = (row.get("name") or "").strip()
        if not name:
            log.warning("Skipping skill id=%s with empty name", row.get("id"))
            failed += 1
            continue
        try:
            embedding = await generate_embedding(name)
            supabase.table("skills").update(
                {"embedding": embedding}
            ).eq("id", row["id"]).execute()
            success += 1
            log.info("[%d/%d] %s -> stored", i, len(rows), name)
        except Exception as exc:  # noqa: BLE001 - blanket so one bad row doesn't kill the batch
            failed += 1
            log.error("[%d/%d] %s -> FAILED (%s)", i, len(rows), name, exc)
        # Soft rate-limit: pause every `batch_size` rows. Gemini's free
        # tier allows 1500 rpm so this is generous, but it makes the job
        # nice neighbour if anything else on the project is calling the
        # API concurrently.
        if i % batch_size == 0 and i < len(rows):
            await asyncio.sleep(sleep_between_batches)

    log.info("Done. success=%d failed=%d", success, failed)
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Rows per batch before the inter-batch sleep (default: 50)",
    )
    parser.add_argument(
        "--sleep-between-batches",
        type=float,
        default=0.5,
        help="Seconds to sleep between batches (default: 0.5)",
    )
    args = parser.parse_args()
    return asyncio.run(
        _run(args.batch_size, args.sleep_between_batches)
    )


if __name__ == "__main__":
    sys.exit(main())
