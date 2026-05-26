#!/usr/bin/env python3
"""Backfill employer apply_url for active jobs stuck on aggregator links.

Fetches each aggregator apply_url, extracts the real employer apply link
(and email/phone when present), and updates the row. Throttled to 1 req/sec.
Idempotent via progress file when run with --apply.

Run from repo root::

    cd apps/backend && python scripts/backfill_apply_urls.py
    cd apps/backend && python scripts/backfill_apply_urls.py --apply

Requires SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

from supabase import create_client  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.job_page_text_extractor import (  # noqa: E402
    AGGREGATOR_DOMAINS,
    is_aggregator,
    merge_resolved_apply_contacts,
    resolve_apply_contacts_from_aggregator_url,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_apply_urls")

PROGRESS_PATH = Path("/tmp/zedcv_apply_url_backfill_progress.json")
THROTTLE_SECONDS = 1.0


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
    """Active jobs whose apply_url hostname is a known aggregator."""
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
    print(f"aggregator_domains: {sorted(AGGREGATOR_DOMAINS)}")

    candidates = _load_candidates(supabase)
    if apply:
        candidates = [
            row
            for row in candidates
            if progress.get(str(row["id"])) != "done"
        ]
    if limit is not None:
        candidates = candidates[:limit]

    stats: dict[str, int] = {}
    samples: list[tuple[str, str, str]] = []
    stuck: list[tuple[str, str, str]] = []

    for row in candidates:
        job_id = str(row["id"])
        title = str(row.get("title") or "")
        original = str(row.get("apply_url") or "")
        contacts = await resolve_apply_contacts_from_aggregator_url(original)
        await asyncio.sleep(THROTTLE_SECONDS)

        resolved = bool(
            contacts.apply_url
            or (
                contacts.apply_email
                and not row.get("apply_email")
            )
            or (
                contacts.contact_phone
                and not row.get("contact_phone")
            )
        )
        if resolved:
            status = "resolved"
            if contacts.apply_url and len(samples) < 5:
                samples.append((job_id, original, contacts.apply_url))
        else:
            status = "unchanged"
            if len(stuck) < 5:
                stuck.append((job_id, title, original))

        stats[status] = stats.get(status, 0) + 1

        if apply:
            patch: dict[str, Any] = {}
            merge_resolved_apply_contacts(
                patch,
                contacts,
                original_apply_url=original,
            )
            if patch:
                supabase.table("jobs").update(patch).eq("id", job_id).execute()
            progress[job_id] = "done"
            _save_progress(progress)

    after = count_aggregator_apply_urls(supabase)
    print(f"aggregator_apply_urls_after: {after}")
    print(f"delta: {before - after}")
    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")
    for job_id, old_url, new_url in samples:
        print(f"  sample {job_id[:8]}: {old_url} -> {new_url}")
    if stuck:
        print("still_unresolvable_sample:")
        for job_id, title, url in stuck:
            print(f"  {job_id[:8]} | {title[:60]} | {url}")

    if not apply:
        print("Dry-run: pass --apply to persist updates.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write resolved URLs to the database (default dry-run)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max jobs this run")
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Ignore /tmp progress file and re-process all aggregator jobs",
    )
    args = parser.parse_args()
    if args.apply:
        log.info("APPLY mode — database and %s may be updated", PROGRESS_PATH)
    return asyncio.run(
        run_backfill(
            apply=args.apply,
            limit=args.limit,
            reset_progress=args.reset_progress,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
