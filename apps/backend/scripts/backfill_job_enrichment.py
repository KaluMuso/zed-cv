#!/usr/bin/env python3
"""Backfill LLM enrichment for existing job rows.

Dry-run by default — prints per-job diffs and a cost estimate. Pass
``--apply`` to write merged skills and NULL-only enum updates.

Run from repo root::

    python apps/backend/scripts/backfill_job_enrichment.py
    python apps/backend/scripts/backfill_job_enrichment.py --apply

Requires SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY), and
OPENROUTER_API_KEY (via Settings / .env).
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

# In the Docker image scripts live at /app/scripts/ and the package at
# /app/app/. In dev they live at apps/backend/scripts/. parent.parent is
# the backend root in both layouts (do not walk up to repo root).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

from supabase import create_client  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.job_enricher import (  # noqa: E402
    JobEnrichment,
    enrich_job_for_backfill,
)
from app.services.job_enrichment import apply_job_enrichment  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_job_enrichment")

PROGRESS_PATH = Path("/tmp/zedcv_backfill_progress.json")
MIN_DESCRIPTION_LEN = 50
# OpenRouter free/paid Flash tiers rate-limit below 1 req/s when the SDK
# also retries 429s — default 2.5s keeps dry-runs under the cap.
DEFAULT_DELAY_SECONDS = 2.5


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


def _existing_skill_names(supabase: Any, job_id: str) -> set[str]:
    links = (
        supabase.table("job_skills")
        .select("skill_id")
        .eq("job_id", job_id)
        .execute()
    )
    names: set[str] = set()
    for row in links.data or []:
        skill_id = row.get("skill_id")
        if not skill_id:
            continue
        sk = (
            supabase.table("skills")
            .select("name")
            .eq("id", skill_id)
            .limit(1)
            .execute()
        )
        if sk.data:
            names.add(str(sk.data[0]["name"]).lower())
    return names


def _enum_arrow(current: str | None, proposed: str | None) -> str | None:
    """Return 'old→new' when a NULL-only write would occur."""
    if current is not None or not proposed:
        return None
    cur = "null" if current is None else current
    return f"{cur}→{proposed}"


def _int_arrow(current: int | None, proposed: int | None) -> str | None:
    if current is not None or proposed is None:
        return None
    cur = "null" if current is None else str(current)
    return f"{cur}→{proposed}"


def _quals_arrow(current: list | None, proposed: list[str]) -> str | None:
    if current or not proposed:
        return None
    return f"null→[{', '.join(proposed[:3])}{'…' if len(proposed) > 3 else ''}]"


def format_enrichment_diff_line(
    job: dict,
    enrichment: JobEnrichment,
    existing_skill_names: set[str],
) -> str:
    """One-line dry-run report for a single job."""
    job_id = str(job.get("id", ""))[:8]
    title = str(job.get("title", ""))[:60]
    new_skills = sorted(
        s for s in enrichment.skills if s.lower() not in existing_skill_names
    )
    parts = [f"{job_id} | {title}"]
    if new_skills:
        parts.append(f"+ skills: [{', '.join(new_skills)}]")
    et = _enum_arrow(job.get("employment_type"), enrichment.employment_type)
    if et:
        parts.append(f"et: {et}")
    wa = _enum_arrow(job.get("work_arrangement"), enrichment.work_arrangement)
    if wa:
        parts.append(f"wa: {wa}")
    emin = _int_arrow(job.get("experience_min_years"), enrichment.experience_min_years)
    if emin:
        parts.append(f"exp_min: {emin}")
    emax = _int_arrow(job.get("experience_max_years"), enrichment.experience_max_years)
    if emax:
        parts.append(f"exp_max: {emax}")
    sen = _enum_arrow(job.get("seniority_level"), enrichment.seniority_level)
    if sen:
        parts.append(f"seniority: {sen}")
    quals = _quals_arrow(
        job.get("qualifications_required"), enrichment.qualifications_required
    )
    if quals:
        parts.append(f"quals: {quals}")
    if len(parts) == 2 and not new_skills:
        parts.append("(no changes)")
    return " | ".join(parts)


async def _process_job(
    supabase: Any,
    job: dict,
    *,
    apply: bool,
    progress: dict[str, str],
) -> tuple[str, bool]:
    """Returns (diff_line, rate_limited)."""
    job_id = str(job["id"])
    if apply and progress.get(job_id) == "done":
        return "", False

    description = (job.get("description") or "").strip()
    if len(description) < MIN_DESCRIPTION_LEN:
        return "", False

    outcome = await enrich_job_for_backfill(
        title=str(job.get("title") or ""),
        company=job.get("company"),
        description=description,
    )
    if not outcome.completed:
        return "", True

    enrichment = outcome.enrichment
    existing = _existing_skill_names(supabase, job_id)
    line = format_enrichment_diff_line(job, enrichment, existing)

    if apply:
        await apply_job_enrichment(
            supabase,
            job_id=job_id,
            job_row=job,
            enrichment=enrichment,
            source="backfill",
        )
        progress[job_id] = "done"
        _save_progress(progress)

    return line, False


async def run_backfill(*, apply: bool, delay_seconds: float) -> int:
    settings = get_settings()
    if not settings.openrouter_api_key:
        log.error("OPENROUTER_API_KEY is not set — cannot call enrich_job")
        return 1

    url = settings.supabase_url
    key = settings.supabase_key
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_KEY must be set")
        return 1
    supabase = create_client(url, key)
    progress = _load_progress()

    result = (
        supabase.table("jobs")
        .select(
            "id, title, company, description, employment_type, work_arrangement, "
            "experience_min_years, experience_max_years, seniority_level, "
            "qualifications_required"
        )
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    jobs = result.data or []
    log.info("Loaded %d active jobs", len(jobs))

    lines: list[str] = []
    processed = 0
    rate_limited = 0
    for job in jobs:
        line, was_limited = await _process_job(
            supabase,
            job,
            apply=apply,
            progress=progress,
        )
        if was_limited:
            rate_limited += 1
            log.warning(
                "Rate limited on job %s — waiting %.1fs before next",
                str(job.get("id", ""))[:8],
                delay_seconds * 3,
            )
            await asyncio.sleep(delay_seconds * 3)
            continue
        if line:
            print(line)
            lines.append(line)
            processed += 1
        await asyncio.sleep(delay_seconds)

    eligible = sum(
        1
        for j in jobs
        if len((j.get("description") or "").strip()) >= MIN_DESCRIPTION_LEN
    )
    # ~$0.062 for 310 jobs at Gemini Flash 2.0 OpenRouter rates (May 2026).
    est_usd = eligible * (0.062 / 310) if eligible else 0.0
    print(
        f"\nEstimated {eligible} jobs × ~700 input tokens + 100 output tokens = "
        f"~${est_usd:.3f} at current OpenRouter pricing for Gemini Flash 2.0."
    )
    mode = "apply" if apply else "dry-run"
    print(f"Processed {processed} jobs this run ({mode}).")
    if rate_limited:
        print(
            f"Rate-limited on {rate_limited} jobs — re-run the same command; "
            f"{'only unfinished jobs are written in apply mode' if apply else 'no progress file was updated'}."
        )
    if not apply:
        print(
            "Dry-run does not write /tmp/zedcv_backfill_progress.json — safe to re-run."
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill job LLM enrichment")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write enrichment to the database (default is dry-run)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Seconds between OpenRouter calls (default {DEFAULT_DELAY_SECONDS})",
    )
    args = parser.parse_args()
    if args.apply:
        log.warning("APPLY mode — database will be updated")
    if args.delay < 1.0:
        log.error("--delay must be >= 1.0 second")
        return 1
    return asyncio.run(
        run_backfill(apply=args.apply, delay_seconds=args.delay)
    )


if __name__ == "__main__":
    raise SystemExit(main())
