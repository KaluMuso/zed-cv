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

# Allow `app.*` imports when executed as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

Status = Literal["green", "yellow", "red"]

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "infra" / "supabase" / "migrations"
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
)
# Latest migration sentinel columns (Track 4e / tier_config).
SCHEMA_SENTINELS: tuple[tuple[str, str], ...] = (
    ("jobs", "is_review_required"),
    ("jobs", "review_reason"),
    ("tier_config", "price_ngwee"),
)


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


def check_lenco_key(settings: Any | None) -> CheckResult:
    key = (settings.lenco_api_key if settings else None) or os.getenv("LENCO_API_KEY", "")
    if key.strip():
        return CheckResult("LENCO_API_KEY set", "green", "key present")
    return CheckResult("LENCO_API_KEY set", "yellow", "empty until Phase 1 cutover")


def check_migration_files() -> CheckResult:
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


def check_rls(supabase) -> CheckResult:
    """RLS enabled on Track-1 audited tables (migration 043 RPC)."""
    try:
        resp = supabase.rpc("schema_guard_rls", {}).execute()
        rows = resp.data or []
    except Exception as exc:
        return CheckResult(
            "RLS on 10 audited tables",
            "yellow",
            "schema_guard_rls RPC missing — apply migration 043; manual SQL: "
            "SELECT relname, relrowsecurity FROM pg_class c JOIN pg_namespace n "
            f"ON n.oid = c.relnamespace WHERE n.nspname='public' AND relname = ANY(...); "
            f"({exc})",
        )
    found = {r.get("table_name") for r in rows}
    missing_tables = [t for t in RLS_TABLES if t not in found]
    off = [r.get("table_name") for r in rows if not r.get("rls_enabled")]
    if missing_tables:
        return CheckResult(
            "RLS on 10 audited tables",
            "red",
            f"tables not found: {missing_tables}",
        )
    if off:
        return CheckResult("RLS on 10 audited tables", "red", f"RLS disabled: {off}")
    return CheckResult("RLS on 10 audited tables", "green", "all 10 tables have RLS enabled")


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
    env_path = Path(__file__).resolve().parents[1] / ".env"
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
