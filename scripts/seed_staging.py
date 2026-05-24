#!/usr/bin/env python3
"""Idempotent synthetic seed for the ZedApply **staging** Supabase project.

Never run against production. Requires service-role credentials for the staging
project only (``STAGING_SUPABASE_URL`` + ``STAGING_SUPABASE_SERVICE_KEY``).

What it seeds
-------------
- ``tier_config``: left to migrations (no overwrite)
- ``canonical_skills``: upserts curated rows from the backend seed module
- 5 synthetic users (free, starter, professional, super_standard, employer persona)
- ~20 fake jobs across finance, mining, and technology
- Subscriptions + sample matches for the free-tier test user

Usage::

    export STAGING_SUPABASE_URL=https://<staging-ref>.supabase.co
    export STAGING_SUPABASE_SERVICE_KEY=<service-role>
    python scripts/seed_staging.py
    python scripts/seed_staging.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = REPO_ROOT / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

PROD_SUPABASE_REF = "chnesgmcuxyhwhzomdov"

# Fixed IDs for idempotent upserts
USER_IDS = {
    "free": "a1000001-0001-4001-8001-000000000001",
    "starter": "a1000001-0001-4001-8001-000000000002",
    "professional": "a1000001-0001-4001-8001-000000000003",
    "super_standard": "a1000001-0001-4001-8001-000000000004",
    "employer": "a1000001-0001-4001-8001-000000000005",
}
CV_ID_FREE = "b2000002-0002-4002-8002-000000000001"

SYNTHETIC_USERS = (
    ("free", "+260971000001", "Staging Free User", "free"),
    ("starter", "+260971000002", "Staging Starter User", "starter"),
    ("professional", "+260971000003", "Staging Pro User", "professional"),
    ("super_standard", "+260971000004", "Staging Super User", "super_standard"),
    ("employer", "+260971000005", "Staging Employer User", "starter"),
)

JOB_TEMPLATES: tuple[dict, ...] = (
    # Finance (7)
    {
        "title": "Accounts Assistant",
        "company": "Staging Finance Co",
        "location": "Lusaka",
        "industry": "finance",
        "description": "Synthetic finance role for staging QA.",
        "requirements": ["bookkeeping", "microsoft excel", "sage evolution"],
    },
    {
        "title": "Internal Auditor",
        "company": "Copperbelt Bank (Staging)",
        "location": "Ndola",
        "industry": "finance",
        "description": "Synthetic audit vacancy — not a real listing.",
        "requirements": ["auditing", "ifrs", "zica"],
    },
    {
        "title": "Credit Analyst",
        "company": "Staging Microfinance",
        "location": "Kitwe",
        "industry": "finance",
        "description": "Synthetic credit role for match testing.",
        "requirements": ["credit analysis", "financial reporting", "sql"],
    },
    {
        "title": "Payroll Officer",
        "company": "ZedApply Staging Payroll Ltd",
        "location": "Lusaka",
        "industry": "finance",
        "description": "Synthetic payroll listing.",
        "requirements": ["payroll", "paye", "microsoft excel"],
    },
    {
        "title": "Tax Consultant",
        "company": "Staging Tax Partners",
        "location": "Remote",
        "industry": "finance",
        "description": "Synthetic remote tax role.",
        "requirements": ["taxation", "vat", "compliance"],
    },
    {
        "title": "Treasury Analyst",
        "company": "Staging Treasury House",
        "location": "Lusaka",
        "industry": "finance",
        "description": "Synthetic treasury role.",
        "requirements": ["treasury", "banking", "forecasting"],
    },
    {
        "title": "Finance Graduate Trainee",
        "company": "Staging Holdings",
        "location": "Lusaka",
        "industry": "finance",
        "description": "Synthetic graduate finance intake.",
        "requirements": ["accounting", "communication", "teamwork"],
    },
    # Mining (7)
    {
        "title": "HSE Officer",
        "company": "Staging Copper Mines",
        "location": "Solwezi",
        "industry": "mining",
        "description": "Synthetic mining HSE role.",
        "requirements": ["hse", "health and safety", "risk management"],
    },
    {
        "title": "Mine Planner",
        "company": "North-West Staging Mining",
        "location": "Kalumbila",
        "industry": "mining",
        "description": "Synthetic mine planning vacancy.",
        "requirements": ["project management", "autocad", "civil engineering"],
    },
    {
        "title": "Maintenance Supervisor",
        "company": "Staging Pit Operations",
        "location": "Chingola",
        "industry": "mining",
        "description": "Synthetic maintenance supervisor role.",
        "requirements": ["troubleshooting", "leadership", "inventory management"],
    },
    {
        "title": "Geology Technician",
        "company": "Staging Exploration Ltd",
        "location": "Mansa",
        "industry": "mining",
        "description": "Synthetic geology technician listing.",
        "requirements": ["research", "data analysis", "report writing"],
    },
    {
        "title": "Procurement Officer — Mining",
        "company": "Staging Supply Chain Mining",
        "location": "Ndola",
        "industry": "mining",
        "description": "Synthetic mining procurement role.",
        "requirements": ["procurement", "negotiation", "cost control"],
    },
    {
        "title": "Environmental Officer",
        "company": "Staging Green Pit",
        "location": "Solwezi",
        "industry": "mining",
        "description": "Synthetic environmental compliance role.",
        "requirements": ["compliance", "environmental management", "hse"],
    },
    {
        "title": "Shift Boss",
        "company": "Staging Underground Ops",
        "location": "Kitwe",
        "industry": "mining",
        "description": "Synthetic underground shift boss role.",
        "requirements": ["leadership", "problem solving", "time management"],
    },
    # Technology (6)
    {
        "title": "Junior Software Developer",
        "company": "Staging Tech Zambia",
        "location": "Lusaka",
        "industry": "technology",
        "description": "Synthetic developer role for staging.",
        "requirements": ["python", "javascript", "git"],
    },
    {
        "title": "IT Support Specialist",
        "company": "Staging ISP",
        "location": "Lusaka",
        "industry": "technology",
        "description": "Synthetic IT support listing.",
        "requirements": ["it support", "troubleshooting", "networking"],
    },
    {
        "title": "Data Analyst",
        "company": "Staging Analytics",
        "location": "Remote",
        "industry": "technology",
        "description": "Synthetic data analyst role.",
        "requirements": ["sql", "python", "power bi"],
    },
    {
        "title": "DevOps Engineer",
        "company": "Staging Cloud ZM",
        "location": "Lusaka",
        "industry": "technology",
        "description": "Synthetic DevOps vacancy.",
        "requirements": ["docker", "kubernetes", "amazon web services"],
    },
    {
        "title": "Cybersecurity Analyst",
        "company": "Staging Secure Ltd",
        "location": "Lusaka",
        "industry": "technology",
        "description": "Synthetic security analyst role.",
        "requirements": ["cybersecurity", "compliance", "risk management"],
    },
    {
        "title": "Product Manager",
        "company": "Staging Product Studio",
        "location": "Lusaka",
        "industry": "technology",
        "description": "Synthetic product manager listing.",
        "requirements": ["project management", "communication", "digital marketing"],
    },
)

log = logging.getLogger("seed_staging")


def _require_staging_credentials() -> tuple[str, str]:
    url = os.environ.get("STAGING_SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("STAGING_SUPABASE_SERVICE_KEY")
        or os.environ.get("STAGING_SUPABASE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or ""
    )
    if not url or not key:
        raise SystemExit(
            "Set STAGING_SUPABASE_URL and STAGING_SUPABASE_SERVICE_KEY "
            "(service role) before running."
        )
    if PROD_SUPABASE_REF in url.lower():
        raise SystemExit(
            f"Refusing to seed: URL still targets production project {PROD_SUPABASE_REF}"
        )
    return url, key


def _upsert_users(client, *, dry_run: bool) -> None:
    for key, phone, name, tier in SYNTHETIC_USERS:
        row = {
            "id": USER_IDS[key],
            "phone": phone,
            "full_name": name,
            "subscription_tier": tier,
            "role": "user",
            "is_active": True,
            "location": "Lusaka",
            "years_experience": 3,
        }
        if dry_run:
            log.info("user %s %s", phone, tier)
            continue
        client.table("users").upsert(row, on_conflict="phone").execute()
        sub = {
            "user_id": USER_IDS[key],
            "tier": tier,
            "status": "active",
            "matches_limit": 99999 if tier == "super_standard" else 50,
        }
        client.table("subscriptions").upsert(sub, on_conflict="user_id").execute()


def _upsert_cv_and_matches(client, job_ids: list[str], *, dry_run: bool) -> None:
    cv_row = {
        "id": CV_ID_FREE,
        "user_id": USER_IDS["free"],
        "file_url": "staging://synthetic/cv-free.pdf",
        "file_type": "pdf",
        "raw_text": "Synthetic CV for staging — accountant with Excel and Sage skills.",
        "parsed_data": {
            "skills": ["Microsoft Excel", "Bookkeeping", "Sage Evolution"],
            "summary": "Staging test CV",
        },
        "is_primary": True,
        "parsing_confidence": 0.9,
    }
    if dry_run:
        log.info("cv + %d matches for free user", min(5, len(job_ids)))
        return
    client.table("cvs").upsert(cv_row, on_conflict="id").execute()
    for idx, job_id in enumerate(job_ids[:5]):
        score = 88.0 - (idx * 3)
        match_row = {
            "user_id": USER_IDS["free"],
            "job_id": job_id,
            "cv_id": CV_ID_FREE,
            "score": score,
            "vector_score": score * 0.5,
            "skill_score": score * 0.2,
            "bonus_score": 5.0,
            "matched_skills": ["Microsoft Excel", "Bookkeeping"],
            "missing_skills": ["ZICA"],
            "explanation": "Synthetic staging match for QA.",
            "status": "new",
        }
        client.table("matches").upsert(match_row, on_conflict="user_id,job_id").execute()


def _upsert_jobs(client, *, dry_run: bool) -> list[str]:
    job_ids: list[str] = []
    closing = date.today() + timedelta(days=45)
    for idx, tmpl in enumerate(JOB_TEMPLATES):
        job_id = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"zedapply-staging-job-{idx}-{tmpl['title']}")
        )
        job_ids.append(job_id)
        row = {
            "id": job_id,
            "title": tmpl["title"],
            "company": tmpl["company"],
            "location": tmpl["location"],
            "description": tmpl["description"],
            "requirements": tmpl["requirements"],
            "apply_email": f"jobs+staging{idx}@example.invalid",
            "source": "manual",
            "quality_score": 80,
            "is_active": True,
            "closing_date": closing.isoformat(),
            "company_description": f"Staging employer — {tmpl['industry']}.",
        }
        if dry_run:
            log.info("job %s (%s)", tmpl["title"], tmpl["industry"])
            continue
        client.table("jobs").upsert(row, on_conflict="id").execute()
    return job_ids


def _seed_canonical_skills(client, *, dry_run: bool) -> None:
    if dry_run:
        log.info("canonical_skills via seed_canonical_skills module")
        return
    from app.services.canonical_skills_seed import (
        curated_fallback_rows,
        seed_canonical_skills,
    )

    rows = curated_fallback_rows()
    seed_canonical_skills(client, rows)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Seed staging Supabase (synthetic only)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args()

    url, key = _require_staging_credentials()
    os.environ.setdefault("SUPABASE_URL", url)
    os.environ.setdefault("SUPABASE_KEY", key)
    os.environ.setdefault("JWT_SECRET", "staging-seed-script-unused")

    from supabase import create_client

    client = create_client(url, key)

    log.info("Seeding staging project at %s", url.split("//")[-1].split(".")[0])
    _seed_canonical_skills(client, dry_run=args.dry_run)
    _upsert_users(client, dry_run=args.dry_run)
    job_ids = _upsert_jobs(client, dry_run=args.dry_run)
    _upsert_cv_and_matches(client, job_ids, dry_run=args.dry_run)
    log.info("Staging seed complete (synthetic data only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
