"""Canonical skill dictionary — scraper raw strings → curated names."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


def normalize_raw_skill(skill: str) -> str:
    """Lowercase trimmed form stored in raw_skill_mappings.raw_name."""
    return skill.strip().lower()


def record_raw_skills(supabase: Client, skill_names: list[str]) -> list[str]:
    """Map ingest skills through the dictionary; track unmapped raw strings.

    For each non-empty skill:
    - If raw_skill_mappings has a row with canonical_id, replace with
      canonical_skills.name.
    - Otherwise upsert/increment raw_skill_mappings (canonical_id NULL) and
      keep the original trimmed string for the job pipeline.
    """
    if not skill_names:
        return []

    out: list[str] = []
    for raw_input in skill_names:
        trimmed = raw_input.strip()
        if not trimmed:
            continue
        key = normalize_raw_skill(trimmed)
        try:
            row_res = (
                supabase.table("raw_skill_mappings")
                .select("id, canonical_id, occurrences")
                .eq("raw_name", key)
                .limit(1)
                .execute()
            )
            rows = row_res.data or []
        except Exception as exc:
            logger.warning(
                "skills_dictionary: lookup failed for %r: %s", key, exc
            )
            out.append(trimmed)
            continue

        if rows:
            mapping = rows[0]
            canon_id = mapping.get("canonical_id")
            if canon_id:
                canon_name = _canonical_name_for_id(supabase, canon_id)
                out.append(canon_name if canon_name else trimmed)
            else:
                _increment_occurrences(supabase, mapping["id"], mapping["occurrences"])
                out.append(trimmed)
            continue

        try:
            supabase.table("raw_skill_mappings").insert(
                {"raw_name": key, "occurrences": 1}
            ).execute()
        except Exception as exc:
            logger.warning(
                "skills_dictionary: insert failed for %r: %s", key, exc
            )
        out.append(trimmed)

    return out


def list_pending_raw_skills(supabase: Client, limit: int = 500) -> list[dict[str, Any]]:
    """Raw skills with no canonical_id, highest occurrences first."""
    result = (
        supabase.table("raw_skill_mappings")
        .select("id, raw_name, occurrences")
        .is_("canonical_id", "null")
        .order("occurrences", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def merge_raw_to_canonical(
    supabase: Client,
    raw_skill_id: UUID,
    canonical_skill_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Attach a raw mapping to a canonical skill (create canonical if needed)."""
    name = canonical_skill_name.strip()
    if not name:
        raise ValueError("canonical_skill_name must not be empty")

    raw_res = (
        supabase.table("raw_skill_mappings")
        .select("id, raw_name, canonical_id, occurrences")
        .eq("id", str(raw_skill_id))
        .limit(1)
        .execute()
    )
    if not raw_res.data:
        raise LookupError("raw_skill_mapping_not_found")

    canon_row = _get_or_create_canonical(supabase, name)
    canon_id = canon_row["id"]

    update_res = (
        supabase.table("raw_skill_mappings")
        .update({"canonical_id": canon_id})
        .eq("id", str(raw_skill_id))
        .execute()
    )
    if not update_res.data:
        raise RuntimeError("raw_skill_mapping_update_failed")

    mapping = update_res.data[0]
    return canon_row, mapping


def _canonical_name_for_id(supabase: Client, canonical_id: str) -> str | None:
    try:
        res = (
            supabase.table("canonical_skills")
            .select("name")
            .eq("id", canonical_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["name"]
    except Exception as exc:
        logger.warning(
            "skills_dictionary: canonical lookup failed for %s: %s",
            canonical_id,
            exc,
        )
    return None


def _increment_occurrences(
    supabase: Client, mapping_id: str, current: int
) -> None:
    try:
        supabase.table("raw_skill_mappings").update(
            {"occurrences": int(current) + 1}
        ).eq("id", mapping_id).execute()
    except Exception as exc:
        logger.warning(
            "skills_dictionary: increment failed for %s: %s", mapping_id, exc
        )


def _get_or_create_canonical(supabase: Client, name: str) -> dict[str, Any]:
    existing = (
        supabase.table("canonical_skills")
        .select("id, name, created_at")
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    inserted = (
        supabase.table("canonical_skills")
        .insert({"name": name})
        .execute()
    )
    if not inserted.data:
        raise RuntimeError("canonical_skill_insert_failed")
    return inserted.data[0]
