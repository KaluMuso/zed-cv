"""Smoke test for Slice F — WhatsApp channel ingest end-to-end.

Run against a real OPENROUTER_API_KEY + SUPABASE_URL/KEY (does NOT need
the feature flag enabled; this script bypasses the webhook and calls the
extractor + ingest pipeline directly).

What it does:
  1. Feeds a representative channel-style job post to job_extractor.
  2. Prints the extracted JSON for human review.
  3. Builds a JobCreate and runs _ingest_one_job → expects "ingested".
  4. Runs _ingest_one_job a second time with the same content → expects
     "duplicate" (proving the fingerprint dedup still catches re-broadcasts).

Usage from repo root:
    cd apps/backend
    python scripts/smoke_slice_f.py

The script writes one row to `jobs` + one to `job_fingerprints` on first
run. To clean up afterwards delete by source_url:
    delete from jobs where source_url like 'whatsapp://channel/smoke-test/%';
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Make `app.*` imports work when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


SAMPLE_MESSAGE = """\
*ACCOUNTANT*

Position: Accountant
Company: ZANACO
Location: Lusaka

Key Responsibilities:
- Prepare monthly financial reports and reconciliations
- Support the year-end audit cycle with external auditors
- Maintain general ledger entries in Sage Evolution
- Liaise with ZRA on tax submissions

Requirements:
- ZICA Licentiate or higher
- 3+ years experience in financial reporting
- Strong Excel and IFRS knowledge
- Experience with Sage Evolution preferred

How to apply: send CV to careers@zanaco.co.zm with subject "Accountant"
Closing date: 30 June 2026
"""


def _require_env() -> None:
    missing = [
        k for k in ("OPENROUTER_API_KEY", "SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY")
        if not os.environ.get(k)
    ]
    if missing:
        print(f"ERROR: missing env vars: {missing}")
        print("Source your .env or export them before running this script.")
        sys.exit(2)


async def main() -> None:
    _require_env()

    from app.core.deps import get_supabase
    from app.services.job_extractor import extract_job_from_message
    from app.api.v1.jobs import _ingest_one_job, _build_aggregator_blacklist
    from app.schemas.jobs import JobCreate, JobSource
    from app.core.config import get_settings

    supabase = get_supabase()
    settings = get_settings()
    blacklist = _build_aggregator_blacklist(settings)

    # ── Step 1: extraction ────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: calling extractor")
    print("=" * 60)
    extracted = await extract_job_from_message(SAMPLE_MESSAGE, supabase)
    if extracted is None:
        print("FAIL: extractor returned None (low confidence or refusal).")
        print("Either the prompt needs tuning or the sample message is too thin.")
        sys.exit(1)

    print(json.dumps(extracted.model_dump(), indent=2, default=str))
    print()
    assert extracted.title, "title must be set"
    assert extracted.description, "description must be set"
    assert extracted.confidence >= 60, f"confidence {extracted.confidence} below floor"
    print(f"OK — extractor returned valid JSON, confidence={extracted.confidence}\n")

    # ── Step 2: first ingest ──────────────────────────────────────────
    print("=" * 60)
    print("STEP 2: first /ingest call (expect ingested=1)")
    print("=" * 60)
    job = JobCreate(
        title=extracted.title,
        company=extracted.company,
        location=extracted.location,
        description=extracted.description,
        apply_url=extracted.apply_url,
        apply_email=extracted.apply_email,
        closing_date=extracted.closing_date,
        skills_required=extracted.skills_required,
        source=JobSource.scraper,
        source_url=f"whatsapp://channel/smoke-test/{os.getpid()}-msg-1",
    )
    status, detail = await _ingest_one_job(supabase, job, blacklist)
    print(f"result: status={status} detail={detail!r}")
    if status != "ingested":
        print(f"FAIL: expected 'ingested', got {status!r} ({detail})")
        print("If this is 'duplicate', a previous smoke run left rows behind —")
        print("delete them from `jobs` and `job_fingerprints` and retry.")
        sys.exit(1)
    print("OK — first ingest succeeded\n")

    # ── Step 3: duplicate ingest ──────────────────────────────────────
    print("=" * 60)
    print("STEP 3: second /ingest call with same content (expect duplicates=1)")
    print("=" * 60)
    # Same payload, but different source_url so we know dedup is by
    # CONTENT (title+company+description), not by source URL.
    job2 = job.model_copy(update={
        "source_url": f"whatsapp://channel/smoke-test/{os.getpid()}-msg-2",
    })
    status2, detail2 = await _ingest_one_job(supabase, job2, blacklist)
    print(f"result: status={status2} detail={detail2!r}")
    if status2 != "duplicate":
        print(f"FAIL: expected 'duplicate', got {status2!r} ({detail2})")
        sys.exit(1)
    print("OK — duplicate ingest correctly short-circuited\n")

    print("=" * 60)
    print("SMOKE TEST PASSED")
    print("=" * 60)
    print("Clean up with:")
    print("  delete from jobs where source_url like 'whatsapp://channel/smoke-test/%';")


if __name__ == "__main__":
    asyncio.run(main())
