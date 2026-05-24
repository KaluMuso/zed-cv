#!/usr/bin/env python3
"""Run the ZedApply readiness audit for production or staging.

Selects the Supabase project URL/key for the target slice, then delegates to
``apps/backend/scripts/production_readiness_audit.py``.

Usage (from repo root)::

    python scripts/production_audit.py --env production
    python scripts/production_audit.py --env staging

Environment variables
---------------------
production (default)
    SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY)

staging
    STAGING_SUPABASE_URL, STAGING_SUPABASE_SERVICE_KEY
    Falls back to SUPABASE_URL / SUPABASE_KEY after sourcing
    ``infra/staging/.env`` if that file exists (not committed).

Optional: pass through ``--skip-db`` to skip live Supabase probes.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_AUDIT = REPO_ROOT / "apps" / "backend" / "scripts" / "production_readiness_audit.py"
STAGING_ENV_FILE = REPO_ROOT / "infra" / "staging" / ".env"
PROD_SUPABASE_REF = "chnesgmcuxyhwhzomdov"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _apply_env_profile(target: str) -> None:
    if target == "staging":
        _load_dotenv(STAGING_ENV_FILE)
        url = os.environ.get("STAGING_SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
        key = (
            os.environ.get("STAGING_SUPABASE_SERVICE_KEY")
            or os.environ.get("STAGING_SUPABASE_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY")
            or ""
        )
        if not url or not key:
            print(
                "staging: set STAGING_SUPABASE_URL and STAGING_SUPABASE_SERVICE_KEY "
                f"(or create {STAGING_ENV_FILE})",
                file=sys.stderr,
            )
            sys.exit(2)
        if PROD_SUPABASE_REF in url.lower():
            print(
                "staging: refusing to run — SUPABASE_URL still points at production project",
                file=sys.stderr,
            )
            sys.exit(2)
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        os.environ.setdefault("SENTRY_ENVIRONMENT", "staging")
        os.environ.setdefault("ENVIRONMENT", "staging")
        return

    url = os.environ.get("SUPABASE_URL", "")
    if url and PROD_SUPABASE_REF not in url.lower():
        print(
            "production: SUPABASE_URL does not look like the canonical prod project "
            f"({PROD_SUPABASE_REF})",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="ZedApply readiness audit (env selector)")
    parser.add_argument(
        "--env",
        choices=("production", "staging"),
        default="production",
        help="Deployment slice to audit (default: production)",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip live Supabase checks",
    )
    args = parser.parse_args()

    _apply_env_profile(args.env)

    cmd = [
        sys.executable,
        str(BACKEND_AUDIT),
        "--env",
        args.env,
    ]
    if args.skip_db:
        cmd.append("--skip-db")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "apps" / "backend")

    completed = subprocess.run(cmd, cwd=str(REPO_ROOT / "apps" / "backend"), env=env)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
