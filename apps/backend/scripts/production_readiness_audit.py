#!/usr/bin/env python3
"""Production readiness audit — run from apps/backend with .env loaded."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Allow `app.*` imports when executed as a script.
sys.path.insert(0, str(_BACKEND_ROOT))

Status = Literal["green", "yellow", "red"]

_REPO_MARKERS = ("CLAUDE.md", "docs/openapi.yaml", "AGENTS.md")
_BACKEND_MARKERS = ("main.py", "requirements.txt", "Dockerfile")


def _find_repo_or_backend_root(start: Path | None = None) -> Path:
    """Walk upward until monorepo root or backend root (container) is found."""
    anchor = (start or Path(__file__)).resolve()

    # 1. Try repo root first (CLAUDE.md, docs/openapi.yaml, AGENTS.md)
    for directory in (anchor.parent, *anchor.parents):
        if any((directory / marker).is_file() for marker in _REPO_MARKERS):
            return directory

    # 2. Container fallback: find backend root via main.py + requirements.txt
    for directory in (anchor.parent, *anchor.parents):
        if all((directory / marker).is_file() for marker in ("main.py", "requirements.txt")):
            return directory

    raise RuntimeError(f"Could not locate repo or backend root from {anchor}")


REPO_ROOT = _find_repo_or_backend_root()
_migrations_path = REPO_ROOT / "infra" / "supabase" / "migrations"
MIGRATIONS_DIR = _migrations_path if _migrations_path.is_dir() else None
EXPECTED_TIERS = ("free", "starter", "professional", "super_standard")
RLS_TABLES = (
    "otp_codes",
    "whatsapp_sessions",
    "user_skills",
    "application_outcomes",
    "skills",
    "skill_aliases",
    "job_skills",
    "job_fingerprints",
    "ai_cache",
    "legal_docs",
    "employers",
    "employer_subscriptions",
    "cv_access_audit",
)
# Column probes for applied migrations (Track 4e+ / tier_config / 081–084).
SCHEMA_SENTINELS: tuple[tuple[str, str], ...] = (
    ("jobs", "is_review_required"),
    ("jobs", "review_reason"),
    ("tier_config", "price_ngwee"),
    ("cv_generations", "match_id"),
    ("saved_jobs", "application_status"),
    ("employers", "verified"),
    ("cover_letter_versions", "version_number"),
    ("cvs", "generated_pdf_path"),
    ("web_push_subscriptions", "endpoint"),
    # 081_welcome_email_sent
    ("users", "welcome_email_sent"),
    # 084_prod_schema_guard_alignment (082 is ledger DML only; 083/085 use RPC checks)
    ("cv_generations", "cv_id"),
    ("users", "whatsapp_alerts"),
    ("users", "language"),
    ("users", "referral_match_bonus"),
)
SECURITY_INVOKER_VIEWS = ("public_jobs", "llm_usage_daily")


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str


def _print_results(results: list[CheckResult]) -> None:
    icons = {"green": "✓", "yellow": "!", "red": "✗"}
    for r in results:
        print(f"  [{icons[r.status]}] {r.name}: {r.detail}")
    counts = {s: sum(1 for r in results if r.status == s) for s in ("green", "yellow", "red")}
    print(
        f"\nSummary: {counts['green']} green, {counts['yellow']} yellow, {counts['red']} red"
    )


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def check_debug(settings: Any | None) -> CheckResult:
    debug = settings.debug if settings else _env_bool("DEBUG", default=True)
    if not debug:
        return CheckResult("DEBUG=false", "green", "debug is disabled")
    return CheckResult("DEBUG=false", "red", "DEBUG=true — disable in production .env")


def check_lenco_url(settings: Any | None) -> CheckResult:
    url = (
        (settings.lenco_api_url if settings else None)
        or os.getenv("LENCO_API_URL", "")
    ).lower()
    lenco_display = settings.lenco_api_url if settings else os.getenv("LENCO_API_URL", "")
    if "api.lenco.co" in url:
        return CheckResult("LENCO_API_URL (production)", "green", lenco_display)
    if "sandbox.lenco.co" in url:
        return CheckResult(
            "LENCO_API_URL (production)",
            "yellow",
            f"still sandbox: {lenco_display}",
        )
    if not url:
        return CheckResult("LENCO_API_URL (production)", "yellow", "LENCO_API_URL unset")
    return CheckResult(
        "LENCO_API_URL (production)",
        "yellow",
        f"unexpected host: {lenco_display}",
    )


def check_sentry(settings: Any | None) -> CheckResult:
    dsn = (settings.sentry_dsn if settings else None) or os.getenv("SENTRY_DSN", "")
    if dsn.strip():
        return CheckResult("SENTRY_DSN set", "green", "DSN configured")
    return CheckResult("SENTRY_DSN set", "yellow", "empty — error tracking disabled")


def check_redis_url() -> CheckResult:
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        return CheckResult("REDIS_URL set", "green", "shared rate-limit storage")
    return CheckResult(
        "REDIS_URL set",
        "yellow",
        "unset — rate limits reset on container recreate",
    )


def check_lenco_key(settings: Any | None) -> CheckResult:
    key = (settings.lenco_api_key if settings else None) or os.getenv("LENCO_API_KEY", "")
    if key.strip():
        return CheckResult("LENCO_API_KEY set", "green", "key present")
    return CheckResult("LENCO_API_KEY set", "yellow", "empty until Phase 1 cutover")


def check_migration_files() -> CheckResult:
    if MIGRATIONS_DIR is None:
        return CheckResult(
            "Migrations on disk",
            "yellow",
            "check from repo (not container)",
        )
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        return CheckResult("Migrations on disk", "red", f"no SQL in {MIGRATIONS_DIR}")
    latest_name = files[-1].name
    return CheckResult(
        "Migrations on disk (001–latest)",
        "green",
        f"{len(files)} files, latest {latest_name}",
    )


def check_schema_sentinels(supabase) -> CheckResult:
    missing: list[str] = []
    for table, column in SCHEMA_SENTINELS:
        try:
            supabase.table(table).select(column).limit(1).execute()
        except Exception as exc:
            msg = str(exc).lower()
            if "42703" in msg or "column" in msg and "does not exist" in msg:
                missing.append(f"{table}.{column}")
            elif "42p01" in msg or "relation" in msg and "does not exist" in msg:
                missing.append(table)
            else:
                return CheckResult(
                    "DB schema sentinels (migrations applied)",
                    "yellow",
                    f"could not probe {table}.{column}: {exc}",
                )
    if missing:
        return CheckResult(
            "DB schema sentinels (migrations applied)",
            "red",
            f"missing: {', '.join(missing)} — apply pending migrations",
        )
    if MIGRATIONS_DIR is None:
        return CheckResult(
            "DB schema sentinels (migrations applied)",
            "green",
            "probes OK (migration files not on disk in container)",
        )
    latest = sorted(MIGRATIONS_DIR.glob("*.sql"))[-1].name
    return CheckResult(
        "DB schema sentinels (migrations applied)",
        "green",
        f"probes OK through latest file {latest}",
    )


def check_tier_config(supabase) -> CheckResult:
    try:
        resp = supabase.table("tier_config").select("tier").execute()
        tiers = {row["tier"] for row in (resp.data or [])}
    except Exception as exc:
        return CheckResult("tier_config rows", "red", str(exc))
    missing = [t for t in EXPECTED_TIERS if t not in tiers]
    if missing:
        return CheckResult("tier_config rows", "red", f"missing tiers: {missing}")
    return CheckResult("tier_config rows", "green", f"all {len(EXPECTED_TIERS)} tiers present")


def check_active_jobs_apply_path(supabase) -> CheckResult:
    try:
        resp = (
            supabase.table("jobs")
            .select("id", count="exact")
            .eq("is_active", True)
            .is_("apply_url", "null")
            .is_("apply_email", "null")
            .execute()
        )
        count = resp.count if resp.count is not None else len(resp.data or [])
    except Exception as exc:
        return CheckResult("Active jobs have apply path", "red", str(exc))
    if count:
        return CheckResult(
            "Active jobs have apply path",
            "red",
            f"{count} job(s) is_active=true with no apply_url or apply_email",
        )
    return CheckResult("Active jobs have apply path", "green", "no orphaned active jobs")


def check_schema_guard_columns_rpc(supabase) -> CheckResult:
    """Migration 083: schema_guard_columns RPC for CI live drift detection."""
    try:
        resp = supabase.rpc("schema_guard_columns", {}).execute()
        rows = resp.data or []
    except Exception as exc:
        return CheckResult(
            "schema_guard_columns RPC (083)",
            "red",
            f"missing or failed — apply migration 083: {exc}",
        )
    if not rows:
        return CheckResult(
            "schema_guard_columns RPC (083)",
            "yellow",
            "RPC returned no rows (empty public schema?)",
        )
    return CheckResult(
        "schema_guard_columns RPC (083)",
        "green",
        f"returns {len(rows)} column row(s)",
    )


def check_security_invoker_views(supabase) -> CheckResult:
    """Migration 085: public_jobs and llm_usage_daily use security_invoker."""
    try:
        resp = supabase.rpc("schema_guard_security_invoker_views", {}).execute()
        rows = resp.data or []
    except Exception as exc:
        return CheckResult(
            "security_invoker views (085)",
            "red",
            f"schema_guard_security_invoker_views missing — apply migrations 085+088: {exc}",
        )
    by_name = {r.get("view_name"): r.get("security_invoker") for r in rows}
    missing = [v for v in SECURITY_INVOKER_VIEWS if v not in by_name]
    if missing:
        return CheckResult(
            "security_invoker views (085)",
            "red",
            f"views not found: {missing}",
        )
    off = [v for v in SECURITY_INVOKER_VIEWS if not by_name.get(v)]
    if off:
        return CheckResult(
            "security_invoker views (085)",
            "red",
            f"security_invoker not enabled: {off}",
        )
    return CheckResult(
        "security_invoker views (085)",
        "green",
        "public_jobs and llm_usage_daily use security_invoker",
    )


def check_rls(supabase) -> CheckResult:
    """RLS enabled on audited tables (schema_guard_rls RPC; 040 + 088 employer)."""
    label = f"RLS on {len(RLS_TABLES)} audited tables"
    try:
        resp = supabase.rpc("schema_guard_rls", {}).execute()
        rows = resp.data or []
    except Exception as exc:
        return CheckResult(
            label,
            "yellow",
            "schema_guard_rls RPC missing — apply migrations 043/088; manual SQL: "
            "SELECT relname, relrowsecurity FROM pg_class c JOIN pg_namespace n "
            f"ON n.oid = c.relnamespace WHERE n.nspname='public' AND relname = ANY(...); "
            f"({exc})",
        )
    found = {r.get("table_name") for r in rows}
    missing_tables = [t for t in RLS_TABLES if t not in found]
    off = [r.get("table_name") for r in rows if not r.get("rls_enabled")]
    if missing_tables:
        return CheckResult(
            label,
            "red",
            f"tables not found: {missing_tables}",
        )
    if off:
        return CheckResult(label, "red", f"RLS disabled: {off}")
    return CheckResult(
        label,
        "green",
        f"all {len(RLS_TABLES)} tables have RLS enabled",
    )


async def check_waha() -> CheckResult:
    from app.services.whatsapp import check_waha_health

    ok = await check_waha_health()
    if ok:
        return CheckResult("WAHA session WORKING", "green", "at least one session WORKING")
    return CheckResult(
        "WAHA session WORKING",
        "red",
        "no WORKING session — OTP/match digests will fail; see AGENTS.md §3.3",
    )


def _load_settings() -> Any | None:
    env_path = _BACKEND_ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def run_audit(*, skip_db: bool) -> list[CheckResult]:
    settings = _load_settings()
    results: list[CheckResult] = [
        check_debug(settings),
        check_lenco_url(settings),
        check_lenco_key(settings),
        check_sentry(settings),
        check_redis_url(),
        check_migration_files(),
    ]

    if skip_db or settings is None:
        results.append(
            CheckResult(
                "Supabase checks",
                "yellow",
                "skipped"
                + (" (--skip-db)" if skip_db else " (incomplete .env)")
                + "; need SUPABASE_URL, SUPABASE_KEY, JWT_SECRET, GEMINI_API_KEY",
            )
        )
    else:
        from app.core.deps import get_supabase

        sb = get_supabase()
        results.extend(
            [
                check_schema_sentinels(sb),
                check_schema_guard_columns_rpc(sb),
                check_security_invoker_views(sb),
                check_tier_config(sb),
                check_active_jobs_apply_path(sb),
                check_rls(sb),
            ]
        )

    if settings is not None:
        results.append(asyncio.run(check_waha()))
    else:
        results.append(
            CheckResult(
                "WAHA session WORKING",
                "yellow",
                "skipped (incomplete .env for WAHA settings)",
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="ZedApply production readiness audit")
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Only env/file checks (no Supabase queries)",
    )
    args = parser.parse_args()
    print("ZedApply production readiness audit\n")
    results = run_audit(skip_db=args.skip_db)
    _print_results(results)
    return 1 if any(r.status == "red" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
