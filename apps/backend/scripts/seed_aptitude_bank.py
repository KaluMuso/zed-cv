#!/usr/bin/env python3
"""Seed aptitude_question_bank with SHL-style items via OpenRouter (admin one-off).

Idempotent: skips a pack when it already has >= 60 rows.

Usage (from repo root):
  cd apps/backend && python scripts/seed_aptitude_bank.py
  docker compose exec zedcv-backend python /app/scripts/seed_aptitude_bank.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/seed_aptitude_bank.py` from apps/backend
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import APIError, OpenAI

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services.openrouter_helpers import get_completion_content

logger = logging.getLogger(__name__)

PACKS = ("numerical", "verbal", "abstract")
TARGET_PER_PACK = 60
DEFAULT_BATCH_SIZE = 50
JSON_RETRY_BATCH_SIZES = (50, 25, 10)
TOKENS_PER_QUESTION = 400
MODEL = "google/gemini-2.0-flash-001"

PACK_PROMPTS = {
    "numerical": (
        "Generate SHL-style numerical reasoning MCQs for African job seekers. "
        "Use charts, percentages, ratios, currency (ZMW). "
    ),
    "verbal": (
        "Generate SHL-style verbal reasoning MCQs: short passages, inference, "
        "true/false/cannot say style as multiple choice."
    ),
    "abstract": (
        "Generate SHL-style abstract reasoning: pattern series, odd-one-out, "
        "next-in-sequence as multiple choice."
    ),
}


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_questions_payload(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(_strip_json_fences(text))
    except json.JSONDecodeError as exc:
        logger.warning("Aptitude seed JSON decode failed: %s", exc)
        return []
    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        logger.warning("Aptitude seed: expected questions array in LLM JSON")
        return []
    return items


def _quality_ok(item: dict[str, Any]) -> bool:
    opts = item.get("options")
    if not isinstance(opts, list) or len(opts) < 4:
        return False
    if not str(item.get("question_text") or "").strip():
        return False
    if not str(item.get("correct_value") or "").strip():
        return False
    for opt in opts:
        if not isinstance(opt, dict) or not opt.get("label") or not opt.get("value"):
            return False
    return True


def _json_retry_sizes(requested: int) -> list[int]:
    """Batch sizes to try after JSON parse failures (largest first)."""
    if requested <= 0:
        return []
    ladder = list(JSON_RETRY_BATCH_SIZES)
    if requested > ladder[0]:
        return [requested, *ladder]
    if requested in ladder:
        start = ladder.index(requested)
        return ladder[start:]
    smaller = [s for s in ladder if s < requested]
    return [requested, *smaller]


def _is_response_format_rejected(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "response_format" in msg or "json_object" in msg


def _completion_create(
    client: OpenAI,
    *,
    prompt: str,
    max_tokens: int,
    use_json_mode: bool,
) -> str:
    kwargs: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "messages": [
            {
                "role": "system",
                "content": "You write fair psychometric test items. Output valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except APIError as exc:
        if use_json_mode and _is_response_format_rejected(exc):
            logger.warning(
                "OpenRouter rejected response_format=json_object (%s); retrying without",
                exc,
            )
            kwargs.pop("response_format", None)
            response = client.chat.completions.create(**kwargs)
            return get_completion_content(response, default="{}")
        raise

    return get_completion_content(response, default="{}")


async def _generate_pack_questions(
    pack: str,
    count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate questions; returns (valid_questions, attempt_log)."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required to seed aptitude bank")

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    attempt_log: list[dict[str, Any]] = []

    def _sync() -> list[dict[str, Any]]:
        json_mode_active = True
        sizes = _json_retry_sizes(count)
        for attempt_idx, batch_size in enumerate(sizes, start=1):
            prompt = (
                f"{PACK_PROMPTS[pack]} Return JSON only: "
                '{"questions": [{"question_text": "...", "options": '
                '[{"label":"A","value":"a"},...4 options], "correct_value": "a", '
                '"difficulty": "medium"}]}'
                f" Generate exactly {batch_size} unique questions."
            )
            max_tokens = max(512, batch_size * TOKENS_PER_QUESTION)
            try:
                content = _completion_create(
                    client,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    use_json_mode=json_mode_active,
                )
            except APIError as exc:
                attempt_log.append(
                    {
                        "attempt": attempt_idx,
                        "batch_size": batch_size,
                        "max_tokens": max_tokens,
                        "json_mode": json_mode_active,
                        "error": f"APIError: {exc}",
                        "parsed": 0,
                        "valid": 0,
                    }
                )
                continue

            raw = _parse_questions_payload(str(content or "{}"))
            valid = [q for q in raw if _quality_ok(q)]
            attempt_log.append(
                {
                    "attempt": attempt_idx,
                    "batch_size": batch_size,
                    "max_tokens": max_tokens,
                    "json_mode": json_mode_active,
                    "parsed": len(raw),
                    "valid": len(valid),
                }
            )
            if valid:
                return valid[:count]

        return []

    valid = await asyncio.to_thread(_sync)
    return valid, attempt_log


def _pack_count(supabase, pack: str) -> int:
    res = (
        supabase.table("aptitude_question_bank")
        .select("id", count="exact")
        .eq("pack", pack)
        .execute()
    )
    if getattr(res, "count", None) is not None:
        return int(res.count)
    return len(res.data or [])


async def seed_pack(pack: str, *, target: int = TARGET_PER_PACK) -> int:
    supabase = get_supabase()
    existing = _pack_count(supabase, pack)
    print(
        f"Starting pack {pack} (target: {target}, currently have: {existing})",
        flush=True,
    )
    if existing >= target:
        logger.info("Pack %s already has %s rows — skipping", pack, existing)
        return 0

    needed = target - existing
    inserted = 0
    while inserted < needed:
        batch = min(DEFAULT_BATCH_SIZE, needed - inserted)
        questions, attempt_log = await _generate_pack_questions(pack, batch)
        if not questions:
            logger.error(
                "Pack %s: batch failed after %s attempts — giving up on this batch",
                pack,
                len(attempt_log),
            )
            for entry in attempt_log:
                logger.error("Pack %s attempt detail: %s", pack, entry)
            break
        rows = [
            {
                "pack": pack,
                "question_text": q["question_text"],
                "options": q["options"],
                "correct_value": q["correct_value"],
                "difficulty": q.get("difficulty") or "medium",
            }
            for q in questions
        ]
        supabase.table("aptitude_question_bank").insert(rows).execute()
        inserted += len(rows)
        logger.info("Pack %s: inserted %s (total new %s)", pack, len(rows), inserted)

    print(f"Pack {pack} summary: inserted {inserted} new rows", flush=True)
    return inserted


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    summary: dict[str, int] = {}
    for pack in PACKS:
        summary[pack] = await seed_pack(pack)
    print("Seed complete — per-pack new rows:", summary, flush=True)
    logger.info("Seed complete. New rows inserted: %s", sum(summary.values()))


if __name__ == "__main__":
    asyncio.run(main())
