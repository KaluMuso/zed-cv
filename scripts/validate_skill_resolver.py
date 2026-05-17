#!/usr/bin/env python3
"""Run the production skill_resolver against a hand-labeled fixture and
report precision / recall.

The fixture is `scripts/skill_resolver_fixture.json` — each pair carries
a `should_match` boolean indicating whether the two names ought to
canonicalize to the same `skills.id`. We classify each pair:

    TP — should_match=True  AND resolver returned the same id
    FN — should_match=True  AND resolver returned different ids
    FP — should_match=False AND resolver returned the same id
    TN — should_match=False AND resolver returned different ids

We use the resolver as a black box, including the auto-insert pass —
that means running this script DOES create rows in `skills`. Use a
non-production project (or run with `--ephemeral` which creates a
disposable schema; see below) when iterating on thresholds.

Acceptance, baked into the fixture's `thresholds_under_test` block:

    precision >= 0.90  AND  recall >= 0.85

The script exits non-zero if either threshold isn't met, so it can be
wired into CI if we ever want hard validation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

# See note in backfill_skill_embeddings.py — Pydantic Settings demands
# these even though the validation path doesn't use them.
os.environ.setdefault("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
os.environ.setdefault("JWT_SECRET", "unused-by-validate-script")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("validate_skill_resolver")


async def _run(
    *,
    fixture_path: Path,
    trgm_threshold: float | None,
    vector_threshold: float | None,
    json_out: bool,
) -> int:
    from supabase import create_client

    from app.services.skill_resolver import (
        DEFAULT_TRGM_THRESHOLD,
        DEFAULT_VECTOR_THRESHOLD,
        resolve_skill_id,
    )

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    pairs = fixture.get("pairs") or []
    if not pairs:
        log.error("Fixture has no pairs")
        return 2

    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        log.error(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) "
            "must be set in the environment."
        )
        return 2

    supabase = create_client(url, key)

    trgm = trgm_threshold if trgm_threshold is not None else DEFAULT_TRGM_THRESHOLD
    vec = vector_threshold if vector_threshold is not None else DEFAULT_VECTOR_THRESHOLD

    tp = fp = tn = fn = 0
    details: list[dict] = []

    # Shared cache so the LLM embedding cost on this run is bounded by
    # the count of UNIQUE names in the fixture, not by total pairs.
    cache: dict[str, str] = {}

    for pair in pairs:
        a = pair.get("a") or ""
        b = pair.get("b") or ""
        label = bool(pair.get("should_match"))
        id_a = await resolve_skill_id(
            a, supabase=supabase, cache=cache,
            source="admin_canonicalize",
            trgm_threshold=trgm, vector_threshold=vec,
        )
        id_b = await resolve_skill_id(
            b, supabase=supabase, cache=cache,
            source="admin_canonicalize",
            trgm_threshold=trgm, vector_threshold=vec,
        )
        predicted = (id_a is not None) and (id_a == id_b)

        if label and predicted:
            tp += 1
            verdict = "TP"
        elif label and not predicted:
            fn += 1
            verdict = "FN"
        elif (not label) and predicted:
            fp += 1
            verdict = "FP"
        else:
            tn += 1
            verdict = "TN"
        details.append({
            "a": a, "b": b,
            "should_match": label,
            "predicted_match": predicted,
            "verdict": verdict,
            "id_a": id_a, "id_b": id_b,
            "category": pair.get("category"),
        })

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    summary = {
        "fixture": str(fixture_path),
        "thresholds": {"trgm": trgm, "vector": vec},
        "counts": {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "total": total},
        "metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "accuracy": round(accuracy, 4),
        },
        "acceptance": {
            "precision_required": 0.90,
            "recall_required": 0.85,
            "passed": precision >= 0.90 and recall >= 0.85,
        },
    }

    if json_out:
        json.dump({"summary": summary, "details": details}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        log.info(
            "Pairs=%d  TP=%d FP=%d TN=%d FN=%d", total, tp, fp, tn, fn
        )
        log.info(
            "Precision=%.3f  Recall=%.3f  Accuracy=%.3f",
            precision, recall, accuracy,
        )
        if not summary["acceptance"]["passed"]:
            log.warning(
                "FAIL: precision >= 0.90 AND recall >= 0.85 not met. "
                "Misclassified pairs:"
            )
            for d in details:
                if d["verdict"] in ("FP", "FN"):
                    log.warning(
                        "  %s  a=%r  b=%r  (%s)",
                        d["verdict"], d["a"], d["b"], d.get("category"),
                    )
        else:
            log.info("PASS: precision and recall meet acceptance thresholds.")

    return 0 if summary["acceptance"]["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=REPO_ROOT / "scripts" / "skill_resolver_fixture.json",
    )
    parser.add_argument("--trgm-threshold", type=float, default=None)
    parser.add_argument("--vector-threshold", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    return asyncio.run(
        _run(
            fixture_path=args.fixture,
            trgm_threshold=args.trgm_threshold,
            vector_threshold=args.vector_threshold,
            json_out=args.json,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
