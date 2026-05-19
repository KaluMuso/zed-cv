#!/usr/bin/env python3
"""Skill canonicalization sweep — cluster duplicate skills and merge.

Loads all skills with embeddings, identifies merge clusters using cosine
similarity + Levenshtein distance, and optionally writes canonical_of
relationships + junction-table FK rewrites.

Run from the repo root:

    # Dry-run (default) — prints cluster report, writes nothing:
    python apps/backend/scripts/canonicalize_skills_sweep.py

    # Apply merges after human review:
    python apps/backend/scripts/canonicalize_skills_sweep.py --apply

Environment variables required:
    SUPABASE_URL, SUPABASE_KEY (or SUPABASE_SERVICE_KEY), GEMINI_API_KEY
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-backfill-scripts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("canonicalize_skills_sweep")

# ── Deny list: pairs that look similar but MUST stay separate ──
# Each tuple is (name_a, name_b) in lowercase. Order doesn't matter.
DENY_PAIRS: list[tuple[str, str]] = [
    ("monitoring", "monitoring and evaluation"),
]


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _token_overlap(a: str, b: str) -> float:
    """Shared-token overlap ratio between two names (case-insensitive)."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    shared = tokens_a & tokens_b
    return len(shared) / min(len(tokens_a), len(tokens_b))


def _both_have_different_digits(a: str, b: str) -> bool:
    """True if both names contain digits but the digit sequences differ."""
    digits_a = "".join(c for c in a if c.isdigit())
    digits_b = "".join(c for c in b if c.isdigit())
    if not digits_a or not digits_b:
        return False
    return digits_a != digits_b


def _is_denied(name_a: str, name_b: str) -> bool:
    """Check if a pair is in the deny list."""
    pair = (name_a.lower(), name_b.lower())
    pair_rev = (pair[1], pair[0])
    return pair in DENY_PAIRS or pair_rev in DENY_PAIRS


def _is_merge_candidate(
    name_a: str,
    name_b: str,
    cosine: float,
    lev: int,
) -> bool:
    """Apply merge eligibility rules from the spec."""
    if _is_denied(name_a, name_b):
        return False
    if _both_have_different_digits(name_a, name_b):
        return False
    if cosine <= 0.85:
        return False
    if lev <= 4:
        return True
    if _token_overlap(name_a, name_b) > 0.6:
        return True
    if cosine < 0.92:
        return False
    return True


def _build_clusters(
    skills: list[dict],
) -> list[list[dict]]:
    """Identify merge clusters from pairwise similarity."""
    n = len(skills)
    parent: list[int] = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    embeddings = [s.get("embedding") for s in skills]

    for i in range(n):
        if embeddings[i] is None:
            continue
        for j in range(i + 1, n):
            if embeddings[j] is None:
                continue
            cosine = _cosine_similarity(embeddings[i], embeddings[j])
            if cosine <= 0.85:
                continue
            lev = _levenshtein(skills[i]["name"], skills[j]["name"])
            if _is_merge_candidate(
                skills[i]["name"], skills[j]["name"], cosine, lev
            ):
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(i)

    return [
        [skills[i] for i in indices]
        for indices in clusters.values()
        if len(indices) > 1
    ]


def _get_ref_counts(supabase: Any, skill_ids: list[str]) -> dict[str, int]:
    """Count references in user_skills + job_skills for given skill IDs."""
    counts: dict[str, int] = {sid: 0 for sid in skill_ids}
    for table in ("user_skills", "job_skills"):
        try:
            res = (
                supabase.table(table)
                .select("skill_id", count="exact")
                .in_("skill_id", skill_ids)
                .execute()
            )
            for row in res.data or []:
                sid = row.get("skill_id")
                if sid in counts:
                    counts[sid] += 1
        except Exception as exc:
            log.warning("ref count query failed for %s: %s", table, exc)
    return counts


def _pick_canonical(cluster: list[dict], ref_counts: dict[str, int]) -> dict:
    """Pick the canonical skill from a cluster.

    Strategy: longest name wins (more specific). Tie-break: most
    references in user_skills + job_skills.
    """
    return max(
        cluster,
        key=lambda s: (len(s["name"]), ref_counts.get(s["id"], 0)),
    )


def _format_cluster_report(
    clusters: list[tuple[dict, list[tuple[dict, float, int]]]],
) -> str:
    """Format the dry-run report."""
    lines: list[str] = []
    total_merges = 0
    total_refs = 0
    for canonical, members in clusters:
        lines.append(f'  Canonical: "{canonical["name"]}"')
        for member, cosine, lev in members:
            refs = member.get("_ref_count", 0)
            total_refs += refs
            total_merges += 1
            lines.append(
                f'    └── merging: "{member["name"]}"'
                f"            (cosine {cosine:.2f}, levenshtein {lev}, refs {refs})"
            )
        lines.append("")

    lines.append(
        f"  Summary: {len(clusters)} clusters, {total_merges} skills to merge, "
        f"{total_refs} references to update."
    )
    return "\n".join(lines)


def _apply_merges(
    supabase: Any,
    clusters: list[tuple[dict, list[tuple[dict, float, int]]]],
) -> dict[str, int]:
    """Execute the merges: set canonical_of, update junction FKs."""
    stats = {"merged": 0, "refs_updated": 0, "errors": 0}

    for canonical, members in clusters:
        for member, cosine, lev in members:
            member_id = member["id"]
            canonical_id = canonical["id"]

            try:
                supabase.table("skills").update({
                    "canonical_of": canonical_id,
                    "merged_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", member_id).execute()
            except Exception as exc:
                log.error(
                    "Failed to set canonical_of on %s: %s", member_id, exc
                )
                stats["errors"] += 1
                continue

            for table, parent_col in [
                ("user_skills", "user_id"),
                ("job_skills", "job_id"),
            ]:
                try:
                    rows = (
                        supabase.table(table)
                        .select(f"{parent_col}, skill_id")
                        .eq("skill_id", member_id)
                        .execute()
                    ).data or []
                    for row in rows:
                        parent_id = row[parent_col]
                        existing = (
                            supabase.table(table)
                            .select("skill_id")
                            .eq(parent_col, parent_id)
                            .eq("skill_id", canonical_id)
                            .limit(1)
                            .execute()
                        ).data
                        if existing:
                            supabase.table(table).delete().eq(
                                parent_col, parent_id
                            ).eq("skill_id", member_id).execute()
                        else:
                            supabase.table(table).update(
                                {"skill_id": canonical_id}
                            ).eq(parent_col, parent_id).eq(
                                "skill_id", member_id
                            ).execute()
                        stats["refs_updated"] += 1
                except Exception as exc:
                    log.error(
                        "FK rewrite failed for %s.%s: %s",
                        table, member_id, exc,
                    )
                    stats["errors"] += 1

            try:
                supabase.table("analytics_events").insert({
                    "event": "skill_merged",
                    "properties": json.dumps({
                        "from_id": member_id,
                        "from_name": member["name"],
                        "to_id": canonical_id,
                        "to_name": canonical["name"],
                        "refs_updated": member.get("_ref_count", 0),
                        "cosine": round(cosine, 4),
                        "levenshtein": lev,
                    }),
                }).execute()
            except Exception:
                pass

            stats["merged"] += 1

    return stats


def _parse_embedding(raw: Any) -> list[float] | None:
    """Parse embedding from DB — may be a string or list."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("["):
            return json.loads(raw)
    return None


def run_sweep(
    supabase: Any,
    *,
    apply: bool = False,
) -> tuple[str, dict[str, int] | None]:
    """Main entry point. Returns (report_text, apply_stats_or_None)."""
    log.info("Loading skills with embeddings...")
    res = supabase.table("skills").select(
        "id, name, embedding, canonical_of"
    ).is_("canonical_of", "null").execute()
    all_skills = res.data or []
    for s in all_skills:
        s["embedding"] = _parse_embedding(s.get("embedding"))
    log.info("Loaded %d non-canonical skills", len(all_skills))

    skills_with_emb = [s for s in all_skills if s.get("embedding")]
    skills_no_emb = [s for s in all_skills if not s.get("embedding")]
    if skills_no_emb:
        log.warning(
            "%d skills have no embedding (skipped): %s",
            len(skills_no_emb),
            [s["name"] for s in skills_no_emb[:10]],
        )

    log.info("Building clusters from %d skills...", len(skills_with_emb))
    clusters_raw = _build_clusters(skills_with_emb)
    log.info("Found %d raw clusters", len(clusters_raw))

    if not clusters_raw:
        return "No merge candidates found.", None

    all_ids = [s["id"] for cluster in clusters_raw for s in cluster]
    ref_counts = _get_ref_counts(supabase, all_ids)
    for cluster in clusters_raw:
        for s in cluster:
            s["_ref_count"] = ref_counts.get(s["id"], 0)

    report_clusters: list[tuple[dict, list[tuple[dict, float, int]]]] = []
    for cluster in clusters_raw:
        canonical = _pick_canonical(cluster, ref_counts)
        members: list[tuple[dict, float, int]] = []
        for s in cluster:
            if s["id"] == canonical["id"]:
                continue
            cosine = _cosine_similarity(
                canonical.get("embedding", []),
                s.get("embedding", []),
            )
            lev = _levenshtein(canonical["name"], s["name"])
            members.append((s, cosine, lev))
        members.sort(key=lambda x: x[1], reverse=True)
        report_clusters.append((canonical, members))

    report_clusters.sort(key=lambda x: len(x[1]), reverse=True)
    report = _format_cluster_report(report_clusters)

    if not apply:
        return report, None

    log.info("Applying %d merges...", sum(len(m) for _, m in report_clusters))
    stats = _apply_merges(supabase, report_clusters)
    log.info("Apply complete: %s", stats)
    return report, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill canonicalization sweep — cluster and merge duplicates."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write merges to the database (default: dry-run).",
    )
    args = parser.parse_args()

    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        log.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) "
            "must be set."
        )
        return 2

    supabase = create_client(url, key)

    report, stats = run_sweep(supabase, apply=args.apply)
    print("\n" + report)
    if stats:
        print(f"\nApply stats: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
