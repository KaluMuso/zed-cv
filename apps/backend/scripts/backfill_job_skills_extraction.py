#!/usr/bin/env python3
"""Phase 2: backfill job_skills for active jobs missing skill links.

Tier 1 — ``enrich_job`` retry on jobs with description >= 400 chars (or any
job not handled by Tier 2).

Tier 2 — deep-link fetch ``source_url``, merge scraped text into
``jobs.description`` when it grows the body, then enrich (description < 400).

No short-description WARNING skip (Phase 1 showed that was not the failure
mode). Throttled to 1 request/second (HTTP + LLM). Idempotent via progress
file in apply mode.

Run from repo root::

    cd apps/backend && python scripts/backfill_job_skills_extraction.py
    cd apps/backend && python scripts/backfill_job_skills_extraction.py --apply

Requires SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY), OPENROUTER_API_KEY.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

from supabase import create_client  # noqa: E402

from app.api.v1.jobs import _strip_html  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.deep_link_enricher import fetch_page  # noqa: E402
from app.services.job_enricher import enrich_job_for_backfill  # noqa: E402
from app.services.job_enrichment import apply_job_enrichment  # noqa: E402
from app.services.job_page_text_extractor import extract_page_text_for_description  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("backfill_job_skills_extraction")

PROGRESS_PATH = Path("/tmp/zedcv_job_skills_extraction_progress.json")
SHORT_DESCRIPTION_CHARS = 400
THROTTLE_SECONDS = 1.0
MIN_ENRICH_CHARS = 1  # Phase 1 WARNING guard removed — do not skip short text

TierName = Literal["tier1", "tier2"]


def _load_progress() -> dict[str, dict[str, str]]:
    if not PROGRESS_PATH.exists():
        return {}
    try:
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read progress file %s: %s", PROGRESS_PATH, exc)
    return {}


def _save_progress(progress: dict[str, dict[str, str]]) -> None:
    PROGRESS_PATH.write_text(
        json.dumps(progress, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _job_ids_with_skills(supabase: Any) -> set[str]:
    res = supabase.table("job_skills").select("job_id").execute()
    return {
        str(row["job_id"])
        for row in (res.data or [])
        if row.get("job_id")
    }


def count_null_skill_jobs(supabase: Any) -> int:
    """Active jobs with zero job_skills rows."""
    jobs_res = (
        supabase.table("jobs")
        .select("id")
        .eq("is_active", True)
        .execute()
    )
    active_ids = {str(r["id"]) for r in (jobs_res.data or []) if r.get("id")}
    if not active_ids:
        return 0
    with_skills = _job_ids_with_skills(supabase)
    return len(active_ids - with_skills)


def _load_candidate_jobs(supabase: Any) -> list[dict[str, Any]]:
    with_skills = _job_ids_with_skills(supabase)
    res = (
        supabase.table("jobs")
        .select(
            "id, title, company, description, source_url, employment_type, "
            "work_arrangement, experience_min_years, experience_max_years, "
            "seniority_level, qualifications_required"
        )
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    out: list[dict[str, Any]] = []
    for row in res.data or []:
        job_id = str(row.get("id") or "")
        if job_id and job_id not in with_skills:
            out.append(row)
    return out


def _tier_for_job(job: dict[str, Any]) -> TierName:
    desc = (job.get("description") or "").strip()
    if len(desc) < SHORT_DESCRIPTION_CHARS and (job.get("source_url") or "").strip():
        return "tier2"
    return "tier1"


async def _scrape_description(source_url: str) -> str:
    status, ctype, body = await fetch_page(source_url)
    if status >= 400 or not body:
        return ""
    if "html" not in ctype.lower() and "<html" not in body[:500].lower():
        return ""
    raw = extract_page_text_for_description(body, source_url)
    return _strip_html(raw) if raw else ""


async def _run_enrich_apply(
    supabase: Any,
    job: dict[str, Any],
    *,
    apply: bool,
    description: str,
) -> tuple[bool, int]:
    """Returns (rate_limited, skills_added)."""
    if len(description.strip()) < MIN_ENRICH_CHARS:
        return False, 0

    outcome = await enrich_job_for_backfill(
        title=str(job.get("title") or ""),
        company=job.get("company"),
        description=description,
    )
    if not outcome.completed:
        return True, 0

    skills_added = 0
    if apply and outcome.enrichment.skills:
        stats = await apply_job_enrichment(
            supabase,
            job_id=str(job["id"]),
            job_row=job,
            enrichment=outcome.enrichment,
            source="skills_backfill",
        )
        skills_added = int(stats.get("skills_added") or 0)
    elif outcome.enrichment.skills:
        skills_added = len(outcome.enrichment.skills)

    return False, skills_added


async def _process_tier2(
    supabase: Any,
    job: dict[str, Any],
    *,
    apply: bool,
    progress: dict[str, dict[str, str]],
) -> tuple[str, bool]:
    job_id = str(job["id"])
    source_url = str(job.get("source_url") or "").strip()
    if not source_url.startswith(("http://", "https://")):
        return "tier2_skip_no_url", False

    scraped = await _scrape_description(source_url)
    await asyncio.sleep(THROTTLE_SECONDS)

    description = (job.get("description") or "").strip()
    merged = description
    if scraped and len(scraped) > len(description):
        merged = scraped
        if apply:
            supabase.table("jobs").update({"description": merged}).eq("id", job_id).execute()
            job = {**job, "description": merged}

    rate_limited, skills_added = await _run_enrich_apply(
        supabase, job, apply=apply, description=merged
    )
    await asyncio.sleep(THROTTLE_SECONDS)

    if apply and not rate_limited:
        progress[job_id] = {"tier": "tier2", "status": "done"}
        _save_progress(progress)

    status = "tier2_enriched" if skills_added else "tier2_no_skills"
    if rate_limited:
        status = "tier2_rate_limited"
    return status, rate_limited


async def _process_tier1(
    supabase: Any,
    job: dict[str, Any],
    *,
    apply: bool,
    progress: dict[str, dict[str, str]],
) -> tuple[str, bool]:
    job_id = str(job["id"])
    description = (job.get("description") or "").strip()

    rate_limited, skills_added = await _run_enrich_apply(
        supabase, job, apply=apply, description=description
    )
    await asyncio.sleep(THROTTLE_SECONDS)

    if apply and not rate_limited:
        progress[job_id] = {"tier": "tier1", "status": "done"}
        _save_progress(progress)

    status = "tier1_enriched" if skills_added else "tier1_no_skills"
    if rate_limited:
        status = "tier1_rate_limited"
    return status, rate_limited


async def run_backfill(
    *,
    apply: bool,
    tier_filter: str,
    limit: int | None,
) -> int:
    settings = get_settings()
    if not settings.openrouter_api_key:
        log.error("OPENROUTER_API_KEY is not set")
        return 1
    if not settings.supabase_url or not settings.supabase_key:
        log.error("SUPABASE_URL and SUPABASE_KEY must be set")
        return 1

    supabase = create_client(settings.supabase_url, settings.supabase_key)
    progress = _load_progress() if apply else {}

    null_before = count_null_skill_jobs(supabase)
    print(f"null_skill_jobs_before: {null_before}")

    candidates = _load_candidate_jobs(supabase)
    tier2_jobs = [j for j in candidates if _tier_for_job(j) == "tier2"]
    tier1_jobs = [j for j in candidates if _tier_for_job(j) == "tier1"]

    if tier_filter == "tier2":
        work = tier2_jobs
    elif tier_filter == "tier1":
        work = tier1_jobs
    else:
        work = tier2_jobs + tier1_jobs

    if apply:
        work = [j for j in work if progress.get(str(j["id"]), {}).get("status") != "done"]

    if limit is not None:
        work = work[:limit]

    log.info(
        "Candidates: %d null-skill (%d tier2, %d tier1); processing %d (%s)",
        len(candidates),
        len(tier2_jobs),
        len(tier1_jobs),
        len(work),
        "apply" if apply else "dry-run",
    )

    stats: dict[str, int] = {}
    for job in work:
        job_id = str(job["id"])
        tier = _tier_for_job(job)
        if tier_filter in ("tier1", "tier2") and tier != tier_filter:
            continue

        if tier == "tier2":
            status, rate_limited = await _process_tier2(
                supabase, job, apply=apply, progress=progress
            )
        else:
            status, rate_limited = await _process_tier1(
                supabase, job, apply=apply, progress=progress
            )

        stats[status] = stats.get(status, 0) + 1
        if rate_limited:
            log.info("Rate limited on %s — re-run later", job_id[:8])
            break

    null_after = count_null_skill_jobs(supabase)
    print(f"null_skill_jobs_after: {null_after}")
    print(f"delta: {null_before - null_after}")
    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")

    if not apply:
        print("Dry-run: no progress file writes; pass --apply to persist.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write enrichment and progress (default dry-run)",
    )
    parser.add_argument(
        "--tier",
        choices=("all", "tier1", "tier2"),
        default="all",
        help="Run only tier1, tier2, or both (default all — tier2 first)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max jobs this run")
    args = parser.parse_args()
    if args.apply:
        log.info("APPLY mode — database and %s may be updated", PROGRESS_PATH)
    return asyncio.run(
        run_backfill(apply=args.apply, tier_filter=args.tier, limit=args.limit)
    )


if __name__ == "__main__":
    raise SystemExit(main())
