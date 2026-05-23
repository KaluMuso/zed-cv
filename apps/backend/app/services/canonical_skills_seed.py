"""Build and insert top canonical_skills rows from job/user skill frequency."""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.services.canonical_skills_seed_data import (
    ACRONYMS,
    CURATED_RAW_TOP_100,
    DISPLAY_OVERRIDES,
    EXTRA_ALIASES,
    NOTES_BY_CANONICAL,
    PARENT_BY_CANONICAL,
)
from app.services.skill_resolver import SKILL_ALIASES
from app.services.skills_dictionary import normalize_raw_skill

logger = logging.getLogger(__name__)

TOP_N = 100
_PAGE_SIZE = 500


@dataclass(frozen=True)
class CanonicalSeedRow:
    name: str
    parent_skill: str | None
    notes: str | None


def _apply_aliases(norm: str) -> str:
    if norm in EXTRA_ALIASES:
        return EXTRA_ALIASES[norm]
    return SKILL_ALIASES.get(norm, norm)


def title_case_canonical(aliased_lower: str) -> str:
    """Turn resolver alias output into a curated display name."""
    text = aliased_lower.strip()
    if not text:
        return ""
    if text in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[text]
    if text in ACRONYMS:
        return text.upper()
    if text.startswith("microsoft "):
        rest = text[len("microsoft ") :]
        return f"Microsoft {_title_words(rest)}"
    if text.startswith("google "):
        rest = text[len("google ") :]
        return f"Google {_title_words(rest)}"
    if "/" in text:
        return "/".join(title_case_canonical(part) for part in text.split("/"))
    return _title_words(text)


def _title_words(text: str) -> str:
    small = {"and", "or", "of", "in", "for", "to", "the", "a", "an"}
    parts = re.split(r"(\s+|-|/)", text)
    out: list[str] = []
    word_idx = 0
    for part in parts:
        if not part or part.isspace() or part in "-/":
            out.append(part)
            continue
        token = part.lower()
        if token in ACRONYMS:
            out.append(token.upper())
        elif word_idx == 0 or token not in small:
            out.append(token.capitalize())
        else:
            out.append(token)
        word_idx += 1
    return "".join(out)


def raw_to_canonical_display(raw: str) -> str:
    norm = normalize_raw_skill(raw)
    if not norm:
        return ""
    aliased = _apply_aliases(norm)
    return title_case_canonical(aliased)


def parent_and_notes_for(name: str) -> tuple[str | None, str | None]:
    parent = PARENT_BY_CANONICAL.get(name)
    notes = NOTES_BY_CANONICAL.get(name)
    return parent, notes


def build_seed_row_from_raw(raw: str) -> CanonicalSeedRow | None:
    name = raw_to_canonical_display(raw)
    if not name:
        return None
    parent, notes = parent_and_notes_for(name)
    return CanonicalSeedRow(name=name, parent_skill=parent, notes=notes)


def collect_raw_skill_counts(supabase: Any) -> Counter[str]:
    """Count normalized raw strings from jobs.requirements and user CV skills."""
    counts: Counter[str] = Counter()
    offset = 0
    while True:
        res = (
            supabase.table("jobs")
            .select("requirements")
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            break
        for row in rows:
            for item in row.get("requirements") or []:
                if isinstance(item, str) and item.strip():
                    counts[normalize_raw_skill(item)] += 1
        if len(rows) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    offset = 0
    while True:
        res = (
            supabase.table("user_skills")
            .select("skills(name)")
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            break
        for row in rows:
            skill_obj = row.get("skills") or {}
            name = skill_obj.get("name") if isinstance(skill_obj, dict) else None
            if isinstance(name, str) and name.strip():
                counts[normalize_raw_skill(name)] += 1
        if len(rows) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    return counts


def rows_from_top_raw(counts: Counter[str], *, limit: int = TOP_N) -> list[CanonicalSeedRow]:
    """Map the top raw strings to deduplicated canonical seed rows."""
    seen_names: set[str] = set()
    rows: list[CanonicalSeedRow] = []
    for raw_norm, _occ in counts.most_common(limit * 3):
        row = build_seed_row_from_raw(raw_norm)
        if not row or row.name in seen_names:
            continue
        seen_names.add(row.name)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def curated_fallback_rows() -> list[CanonicalSeedRow]:
    """Static top-100 Zambia-relevant skills when the database has no frequency data."""
    return rows_from_top_raw(
        Counter({r: 100 - i for i, r in enumerate(CURATED_RAW_TOP_100)})
    )


def seed_canonical_skills(
    supabase: Any,
    *,
    dry_run: bool = False,
    use_curated_fallback: bool = True,
) -> list[CanonicalSeedRow]:
    """Insert up to TOP_N canonical_skills rows; return rows written (or planned)."""
    counts = collect_raw_skill_counts(supabase)
    rows = rows_from_top_raw(counts) if counts else []
    if len(rows) < TOP_N and use_curated_fallback:
        for row in curated_fallback_rows():
            if row.name not in {r.name for r in rows}:
                rows.append(row)
            if len(rows) >= TOP_N:
                break
        rows = rows[:TOP_N]

    if dry_run:
        return rows

    inserted: list[CanonicalSeedRow] = []
    for row in rows:
        payload = {
            "name": row.name,
            "parent_skill": row.parent_skill,
            "notes": row.notes,
        }
        try:
            existing = (
                supabase.table("canonical_skills")
                .select("id, name")
                .eq("name", row.name)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
            res = supabase.table("canonical_skills").insert(payload).execute()
            if res.data:
                inserted.append(row)
        except Exception as exc:
            logger.warning("canonical_skills insert failed for %r: %s", row.name, exc)
    return inserted if not dry_run else rows
