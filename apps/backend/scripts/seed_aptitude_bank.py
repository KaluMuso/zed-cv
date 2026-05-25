#!/usr/bin/env python3
"""Seed aptitude_question_bank with SHL-style items via OpenRouter (admin one-off).

Idempotent: tops up each pack to 60 rows; skips rows whose question_text hash
already exists in the bank.

Usage (from repo root):
  cd apps/backend && python scripts/seed_aptitude_bank.py
  docker compose exec zedcv-backend python /app/scripts/seed_aptitude_bank.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
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
BATCH_SIZE = 10
JSON_RETRY_BATCH_SIZES = (50, 25, 10)
TOKENS_PER_QUESTION = 400
MODEL = "google/gemini-2.0-flash-001"
RETRY_PACKS = frozenset({"verbal", "abstract"})
MIN_PACK_VALID_BEFORE_GIVE_UP = 50
MAX_GENERATION_RETRIES = 3
RETRY_TEMPERATURES = (0.7, 1.0, 1.2)
RETRY_MODELS = (
    "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3-haiku",
)

VALID_DIFFICULTIES = frozenset({"easy", "medium", "hard"})
VERBAL_OPTION_VALUES = frozenset({"true", "false", "cannot_say"})

PACK_PROMPTS = {
    "numerical": (
        "Generate SHL-style numerical reasoning MCQs for African job seekers. "
        "Use charts, percentages, ratios, currency (ZMW). "
    ),
    "verbal": (
        "Generate SHL-style verbal reasoning MCQs: short passages with inference. "
        "Respond with EXACTLY 3 options: 'true', 'false', 'cannot_say'. "
        "No other options."
    ),
    "abstract": (
        "Generate SHL-style abstract reasoning: pattern series, odd-one-out, "
        "next-in-sequence as multiple choice."
    ),
}

_JSON_SCHEMA_BY_PACK = {
    "numerical": (
        '{"questions": [{"question_text": "...", "options": '
        '[{"label":"A","value":"a"},...4 options], "correct_value": "a", '
        '"difficulty": "medium"}]}'
    ),
    "verbal": (
        '{"questions": [{"question_text": "...", "options": '
        '[{"label":"T","value":"true"},{"label":"F","value":"false"},'
        '{"label":"C","value":"cannot_say"}], "correct_value": "true", '
        '"difficulty": "medium"}]}'
    ),
    "abstract": (
        '{"questions": [{"question_text": "...", "options": '
        '[{"label":"A","value":"a"},...4 options], "correct_value": "a", '
        '"difficulty": "medium"}]}'
    ),
}

VERBAL_EXAMPLE_BLOCK = (
    "\n\nExample format:\n"
    'Passage: "All interns must submit timesheets by Friday."\n'
    "Question: Can we infer that interns work five days a week?\n"
    'Options: [{"label":"T","value":"true"},{"label":"F","value":"false"},'
    '{"label":"C","value":"cannot_say"}]\n'
    'correct_value: "cannot_say"\n'
)

ABSTRACT_EXAMPLE_BLOCK = (
    "\n\nExample format:\n"
    "Question: Which shape completes the sequence? [▲, ■, ▲, ■, ?]\n"
    'Options: A) ▲ B) ■ C) ● D) ◆\n'
    'correct_value: "a"\n'
)


@dataclass
class PackSeedResult:
    pack: str
    target: int
    inserted: int
    final_count: int
    retries: int
    skipped: bool


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


def _normalized_option_values(opts: list[Any]) -> list[str]:
    values: list[str] = []
    for opt in opts:
        if not isinstance(opt, dict) or not opt.get("label") or not opt.get("value"):
            return []
        values.append(str(opt["value"]).strip().lower())
    return values


def _quality_ok(item: dict[str, Any], pack: str) -> bool:
    if not str(item.get("question_text") or "").strip():
        return False

    difficulty = str(item.get("difficulty") or "medium").strip().lower()
    if difficulty not in VALID_DIFFICULTIES:
        return False

    opts = item.get("options")
    if not isinstance(opts, list):
        return False

    option_values = _normalized_option_values(opts)
    if len(option_values) != len(opts):
        return False

    correct = str(item.get("correct_value") or "").strip().lower()
    if not correct:
        return False

    if pack == "verbal":
        if len(opts) != 3:
            return False
        if set(option_values) != VERBAL_OPTION_VALUES:
            return False
        return correct in VERBAL_OPTION_VALUES

    if pack == "numerical":
        expected_len = 4
    elif pack == "abstract":
        expected_len = 4
    else:
        return False

    if len(opts) != expected_len:
        return False
    return correct in option_values


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
    model: str,
    temperature: float,
) -> str:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
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


def _question_text_hash(question_text: str) -> str:
    normalized = " ".join(str(question_text).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _existing_hashes_for_pack(supabase, pack: str) -> set[str]:
    res = (
        supabase.table("aptitude_question_bank")
        .select("question_text")
        .eq("pack", pack)
        .execute()
    )
    hashes: set[str] = set()
    for row in res.data or []:
        text = row.get("question_text")
        if text:
            hashes.add(_question_text_hash(str(text)))
    return hashes


def _build_user_prompt(
    pack: str,
    count: int,
    *,
    retry_index: int = 0,
) -> str:
    base = PACK_PROMPTS[pack]
    extra = ""
    if retry_index >= 1:
        if pack == "verbal":
            extra = VERBAL_EXAMPLE_BLOCK
        elif pack == "abstract":
            extra = ABSTRACT_EXAMPLE_BLOCK
    schema_hint = _JSON_SCHEMA_BY_PACK.get(pack, _JSON_SCHEMA_BY_PACK["numerical"])
    return (
        f"{base}{extra} Return JSON only: {schema_hint} "
        f"Generate exactly {count} unique questions."
    )


def _generate_pack_questions_sync(
    pack: str,
    count: int,
    *,
    temperature: float = 0.5,
    model: str = MODEL,
    retry_index: int = 0,
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
    json_mode_active = True
    sizes = _json_retry_sizes(count)

    for attempt_idx, batch_size in enumerate(sizes, start=1):
        prompt = _build_user_prompt(pack, batch_size, retry_index=retry_index)
        max_tokens = max(512, batch_size * TOKENS_PER_QUESTION)
        try:
            content = _completion_create(
                client,
                prompt=prompt,
                max_tokens=max_tokens,
                use_json_mode=json_mode_active,
                model=model,
                temperature=temperature,
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
        valid = [q for q in raw if _quality_ok(q, pack)]
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
            return valid[:count], attempt_log

    return [], attempt_log


async def _generate_pack_questions(
    pack: str,
    count: int,
    *,
    temperature: float = 0.5,
    model: str = MODEL,
    retry_index: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return await asyncio.to_thread(
        _generate_pack_questions_sync,
        pack,
        count,
        temperature=temperature,
        model=model,
        retry_index=retry_index,
    )


async def _generate_pack_questions_with_retries(
    pack: str,
    count: int,
    *,
    needed_remaining: int | None = None,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """Retry verbal/abstract batches when too few valid questions are returned."""
    retries_used = 0
    last_questions: list[dict[str, Any]] = []
    last_attempt_log: list[dict[str, Any]] = []

    for attempt in range(MAX_GENERATION_RETRIES):
        temperature = RETRY_TEMPERATURES[attempt]
        model = RETRY_MODELS[attempt]
        retry_index = attempt
        request_count = count
        if attempt >= 1 and needed_remaining is not None:
            request_count = min(needed_remaining, MIN_PACK_VALID_BEFORE_GIVE_UP)
        questions, attempt_log = await _generate_pack_questions(
            pack,
            request_count,
            temperature=temperature,
            model=model,
            retry_index=retry_index,
        )
        last_questions = questions
        last_attempt_log = attempt_log
        min_acceptable = min(request_count, MIN_PACK_VALID_BEFORE_GIVE_UP)
        if len(questions) >= min_acceptable:
            return questions, retries_used, attempt_log
        if attempt < MAX_GENERATION_RETRIES - 1:
            retries_used += 1
            logger.warning(
                "Pack %s: attempt %s returned %s/%s valid — retrying (temp=%s, model=%s)",
                pack,
                attempt + 1,
                len(questions),
                request_count,
                temperature,
                model,
            )

    return last_questions, retries_used, last_attempt_log


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


def _format_pack_summary(result: PackSeedResult) -> str:
    if result.skipped:
        return f"{result.pack}: {result.final_count}/{result.target} (already complete, skipped)"
    retry_note = (
        f" (took {result.retries} {'retry' if result.retries == 1 else 'retries'})"
        if result.retries
        else ""
    )
    return (
        f"{result.pack}: {result.final_count}/{result.target} inserted"
        f"{retry_note}"
    )


async def _seed_pack_once(
    supabase,
    pack: str,
    *,
    target: int,
    seen_hashes: set[str],
) -> tuple[int, int]:
    """Insert up to target rows for pack; returns (inserted, batch_retries)."""
    existing = _pack_count(supabase, pack)
    print(
        f"Starting pack {pack} (target: {target}, currently have: {existing})",
        flush=True,
    )
    if existing >= target:
        return 0, 0

    needed = target - existing
    inserted = 0
    total_retries = 0

    while inserted < needed:
        batch = min(BATCH_SIZE, needed - inserted)
        attempt_log: list[dict[str, Any]] = []
        if pack in RETRY_PACKS:
            questions, batch_retries, attempt_log = await _generate_pack_questions_with_retries(
                pack,
                batch,
                needed_remaining=needed - inserted,
            )
            total_retries += batch_retries
        else:
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

        rows: list[dict[str, Any]] = []
        for q in questions:
            text = str(q["question_text"])
            q_hash = _question_text_hash(text)
            if q_hash in seen_hashes:
                continue
            seen_hashes.add(q_hash)
            rows.append(
                {
                    "pack": pack,
                    "question_text": text,
                    "options": q["options"],
                    "correct_value": q["correct_value"],
                    "difficulty": str(q.get("difficulty") or "medium").strip().lower(),
                }
            )

        if not rows:
            logger.warning(
                "Pack %s: all %s generated questions were duplicates — skipping batch",
                pack,
                len(questions),
            )
            continue

        supabase.table("aptitude_question_bank").insert(rows).execute()
        inserted += len(rows)
        logger.info("Pack %s: inserted %s (total new %s)", pack, len(rows), inserted)

    print(f"Pack {pack} summary: inserted {inserted} new rows", flush=True)
    return inserted, total_retries


async def _seed_pack_with_summary(pack: str, *, target: int = TARGET_PER_PACK) -> PackSeedResult:
    supabase = get_supabase()
    existing = _pack_count(supabase, pack)
    if existing >= target:
        logger.info("Pack %s already has %s rows — skipping", pack, existing)
        return PackSeedResult(
            pack=pack,
            target=target,
            inserted=0,
            final_count=existing,
            retries=0,
            skipped=True,
        )

    seen_hashes = _existing_hashes_for_pack(supabase, pack)
    inserted = 0
    total_retries = 0

    for pack_round in range(MAX_GENERATION_RETRIES):
        round_inserted, round_retries = await _seed_pack_once(
            supabase,
            pack,
            target=target,
            seen_hashes=seen_hashes,
        )
        inserted += round_inserted
        total_retries += round_retries
        final_count = _pack_count(supabase, pack)
        if final_count >= target:
            break
        if pack not in RETRY_PACKS or final_count >= MIN_PACK_VALID_BEFORE_GIVE_UP:
            break
        if pack_round < MAX_GENERATION_RETRIES - 1:
            total_retries += 1
            logger.warning(
                "Pack %s: only %s/%s rows — re-running seed (round %s)",
                pack,
                final_count,
                target,
                pack_round + 2,
            )

    final_count = _pack_count(supabase, pack)
    return PackSeedResult(
        pack=pack,
        target=target,
        inserted=inserted,
        final_count=final_count,
        retries=total_retries,
        skipped=False,
    )


async def seed_pack(pack: str, *, target: int = TARGET_PER_PACK) -> int:
    result = await _seed_pack_with_summary(pack, target=target)
    return result.inserted


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    results: list[PackSeedResult] = []
    total_inserted = 0
    for pack in PACKS:
        result = await _seed_pack_with_summary(pack)
        results.append(result)
        total_inserted += result.inserted

    for result in results:
        logger.info(_format_pack_summary(result))
    print("Seed complete — per-pack new rows:", {r.pack: r.inserted for r in results}, flush=True)
    logger.info("Seed complete. New rows inserted: %s", total_inserted)


if __name__ == "__main__":
    asyncio.run(main())
