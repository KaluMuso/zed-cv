#!/usr/bin/env python3
"""Generate infra/supabase/migrations/063_seed_legal_docs.sql from docs/legal_content/."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.api.v1.legal import _render_and_sanitise  # noqa: E402

SLUG_FILES = {
    "terms": "terms_of_service.md",
    "privacy": "privacy_policy.md",
    "refund": "refund_policy.md",
    "cookies": "cookie_policy.md",
}

VERSION = "1.0.0"
CONTENT_DIR = ROOT / "docs" / "legal_content"
OUT = ROOT / "infra" / "supabase" / "migrations" / "063_seed_legal_docs.sql"


def sql_quote(value: str) -> str:
    return value.replace("'", "''")


def dollar_tag(prefix: str, body: str) -> str:
    tag = prefix
    n = 0
    while f"${tag}$" in body:
        n += 1
        tag = f"{prefix}{n}"
    return tag


def emit_block(prefix: str, body: str) -> str:
    tag = dollar_tag(prefix, body)
    return f"${tag}$\n{body}\n${tag}$"


def main() -> None:
    lines = [
        "-- 063 — Seed legal_docs with ZDPA-compliant Zed Apply policies",
        "-- Source of truth: docs/legal_content/*.md",
        "-- Idempotent: upserts by slug so re-run is safe.",
        "",
        "BEGIN;",
        "",
    ]
    for slug, filename in SLUG_FILES.items():
        md_path = CONTENT_DIR / filename
        if not md_path.is_file():
            raise SystemExit(f"Missing {md_path}")
        content_md = md_path.read_text(encoding="utf-8")
        content_html = _render_and_sanitise(content_md)
        lines.append(f"-- {filename} -> slug '{slug}'")
        lines.append(
            "INSERT INTO legal_docs (slug, version, content_md, content_html, last_modified_at)"
        )
        lines.append("VALUES (")
        lines.append(f"  '{slug}',")
        lines.append(f"  '{VERSION}',")
        lines.append(f"  {emit_block(f'md_{slug}', content_md)},")
        lines.append(f"  {emit_block(f'html_{slug}', content_html)},")
        lines.append("  NOW()")
        lines.append(")")
        lines.append("ON CONFLICT (slug) DO UPDATE SET")
        lines.append("  version = EXCLUDED.version,")
        lines.append("  content_md = EXCLUDED.content_md,")
        lines.append("  content_html = EXCLUDED.content_html,")
        lines.append("  last_modified_at = EXCLUDED.last_modified_at;")
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
