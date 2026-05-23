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

from openai import OpenAI

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services.openrouter_helpers import get_completion_content

logger = logging.getLogger(__name__)

PACKS = ("numerical", "verbal", "abstract")
TARGET_PER_PACK = 60
BATCH_SIZE = 10
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
    data = json.loads(_strip_json_fences(text))
    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("Expected questions array in LLM JSON")
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


async def _generate_pack_questions(pack: str, count: int) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required to seed aptitude bank")

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    prompt = (
        f"{PACK_PROMPTS[pack]} Return JSON only: "
        '{"questions": [{"question_text": "...", "options": '
        '[{"label":"A","value":"a"},...4 options], "correct_value": "a", '
        '"difficulty": "medium"}]}'
        f" Generate exactly {count} unique questions."
    )

    def _sync() -> list[dict[str, Any]]:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=8000,
            temperature=0.5,
            messages=[
                {
                    "role": "system",
                    "content": "You write fair psychometric test items. Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = get_completion_content(response, default="{}")
        raw = _parse_questions_payload(str(content or "{}"))
        return [q for q in raw if _quality_ok(q)]

    return await asyncio.to_thread(_sync)


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
    if existing >= target:
        logger.info("Pack %s already has %s rows — skipping", pack, existing)
        return 0

    needed = target - existing
    inserted = 0
    while inserted < needed:
        batch = min(BATCH_SIZE, needed - inserted)
        questions = await _generate_pack_questions(pack, batch)
        if not questions:
            logger.warning("Pack %s: LLM returned no valid questions", pack)
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

    return inserted


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    total = 0
    for pack in PACKS:
        total += await seed_pack(pack)
    logger.info("Seed complete. New rows inserted: %s", total)


if __name__ == "__main__":
    asyncio.run(main())
