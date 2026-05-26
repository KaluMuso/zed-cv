#!/usr/bin/env python3
"""Apply tightened canonical_skills cleanup then re-seed from curated list."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))

QUALIFICATION_RE = re.compile(
    r"(Years|Experience|Minimum|Must|Should|Required|Bachelor|Diploma|Certificate|"
    r"Membership|Knowledge of|Ability to)",
    re.IGNORECASE,
)
PREFIX_RE = re.compile(
    r"^(Honest,|Strong |Good |Excellent |Ability to |Knowledge of |Physically |Clean )",
    re.IGNORECASE,
)


def _word_count(name: str) -> int:
    return len([w for w in name.strip().split() if w])


def is_polluted(name: str) -> bool:
    return (
        len(name) > 60
        or bool(QUALIFICATION_RE.search(name))
        or name.endswith(".")
        or "," in name
        or ":" in name
        or "lincence" in name.lower()
        or bool(PREFIX_RE.search(name))
        or _word_count(name) > 4
    )


def main() -> int:
    from supabase import create_client

    from app.services.canonical_skills_seed import seed_canonical_skills

    url = os.environ.get("SUPABASE_URL", "https://chnesgmcuxyhwhzomdov.supabase.co")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not key:
        print("SUPABASE_KEY required", file=sys.stderr)
        return 2

    sb = create_client(url, key)
    offset = 0
    all_rows: list[dict] = []
    while True:
        res = sb.table("canonical_skills").select("id,name").range(offset, offset + 499).execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    polluted = [r for r in all_rows if is_polluted(r["name"])]
    print(f"before_total={len(all_rows)} polluted_count={len(polluted)}")

    for row in polluted:
        sb.table("canonical_skills").delete().eq("id", row["id"]).execute()

    remaining_res = sb.table("canonical_skills").select("id,name").execute()
    remaining = remaining_res.data or []
    print(f"after_cleanup_total={len(remaining)}")
    for r in sorted(remaining, key=lambda x: len(x["name"]), reverse=True)[:15]:
        print(f"  {len(r['name']):3d}  {r['name']}")

    inserted = seed_canonical_skills(sb, dry_run=False)
    final_res = sb.table("canonical_skills").select("id", count="exact").execute()
    final_count = final_res.count if final_res.count is not None else len(final_res.data or [])
    print(f"seeded_new={len(inserted)} final_total={final_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
