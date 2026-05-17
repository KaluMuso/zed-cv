"""Job-search preferences routes — GET + PATCH /api/v1/preferences.

Backs the Preferences tab on /profile. One row per user in
user_preferences (migration 026). Auto-created on first GET so the
frontend never has to handle the "row doesn't exist yet" case.

Distinct from /api/v1/profile/preferences in profile.py — that endpoint
covers notification prefs (whatsapp_alerts, language). This one covers
job-search prefs (target_roles, salary, work arrangement, etc.).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_supabase, get_current_user_id
from app.schemas.preferences import (
    JobPreferences,
    JobPreferencesUpdate,
    IndustryExperience,
    PreferredLanguage,
    MAX_TARGET_ROLES,
    MAX_LANGUAGES,
    MAX_INDUSTRIES,
    MAX_REGIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["Preferences"])


# Fields the auto-populate path writes. Used by the API layer to build
# the per-field "Auto-populated from CV" hint the frontend renders.
_AUTO_POPULATE_FIELDS = (
    "target_roles",
    "languages",
    "industries",
    "acceptable_regions",
)


def _row_to_model(row: dict[str, Any]) -> JobPreferences:
    """Coerce a raw Supabase row into the JobPreferences response shape.

    Handles two quirks of the Supabase-py JSONB read path:
      - JSONB columns sometimes arrive as JSON-stringified text when
        the table was created with the default ::jsonb cast; the
        json-coerce here is defensive against that.
      - Datetime columns arrive as ISO 8601 strings; Pydantic accepts
        those natively but we still pass them through .model_validate
        so the response always serialises to the same shape.
    """
    languages_raw = row.get("languages") or []
    industries_raw = row.get("industries") or []
    extras_raw = row.get("extras") or {}

    # PostgREST occasionally hands back JSONB as a string when the
    # column was created with default 'jsonb' and the response is
    # routed through certain proxies. Tolerate that.
    languages = _coerce_jsonb_list(languages_raw)
    industries = _coerce_jsonb_list(industries_raw)
    extras = _coerce_jsonb_dict(extras_raw)

    typed_languages = [PreferredLanguage(**lang) for lang in languages if isinstance(lang, dict)]
    typed_industries = [
        IndustryExperience(**ind) for ind in industries if isinstance(ind, dict)
    ]

    auto_populated_at = row.get("auto_populated_at")
    manually_updated_at = row.get("manually_updated_at")

    return JobPreferences(
        target_roles=list(row.get("target_roles") or []),
        target_roles_source=row.get("target_roles_source") or "user_provided",
        salary_min=row.get("salary_min"),
        salary_max=row.get("salary_max"),
        salary_currency=row.get("salary_currency") or "ZMW",
        salary_frequency=row.get("salary_frequency"),
        preferred_work_arrangement=row.get("preferred_work_arrangement"),
        willing_to_relocate=bool(row.get("willing_to_relocate") or False),
        acceptable_regions=list(row.get("acceptable_regions") or []),
        languages=typed_languages,
        industries=typed_industries,
        extras=extras,
        auto_populated_at=auto_populated_at,
        manually_updated_at=manually_updated_at,
        auto_populated_fields=_compute_auto_populated_fields(row),
    )


def _compute_auto_populated_fields(row: dict[str, Any]) -> list[str]:
    """Which fields look auto-populated *and* haven't been manually edited.

    Heuristic: if `auto_populated_at` is set, the field is non-empty,
    AND `manually_updated_at` is either NULL or earlier than
    `auto_populated_at`, treat it as auto-populated for badge purposes.

    Once a user PATCHes the row, manually_updated_at advances past
    auto_populated_at and all badges drop — at that point we can't tell
    which individual field the user touched, so we conservatively
    un-badge everything. A precise per-field history would need a
    side table; not worth the complexity for a UI hint.
    """
    auto_at = row.get("auto_populated_at")
    if not auto_at:
        return []
    manual_at = row.get("manually_updated_at")
    if manual_at and _coerce_dt(manual_at) > _coerce_dt(auto_at):
        return []
    out: list[str] = []
    if row.get("target_roles_source") in ("cv_inferred", "mixed") and row.get(
        "target_roles"
    ):
        out.append("target_roles")
    if row.get("languages"):
        out.append("languages")
    if row.get("industries"):
        out.append("industries")
    if row.get("acceptable_regions"):
        out.append("acceptable_regions")
    return out


def _coerce_dt(v: Any) -> datetime:
    """Best-effort datetime coercion. Falls back to epoch on garbage."""
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.fromtimestamp(0, tz=timezone.utc)


def _coerce_jsonb_list(v: Any) -> list[Any]:
    """Coerce a possibly-stringified JSONB array to a list."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            import json
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _coerce_jsonb_dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            import json
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def _get_or_create_row(user_id: str, supabase) -> dict[str, Any]:
    """Return the user's user_preferences row; create an empty one if absent.

    Auto-create on first GET means the frontend never has to handle a
    404. Idempotent — the INSERT uses upsert(ignore_duplicates) so a
    racing call doesn't 23505.
    """
    existing = (
        supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
    )
    if existing.data:
        return existing.data[0]

    try:
        supabase.table("user_preferences").upsert(
            {"user_id": user_id},
            on_conflict="user_id",
            ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        # Insert race: another concurrent request may have just made
        # the row. Re-read below; if it's still missing, something's
        # genuinely wrong.
        logger.warning("user_preferences upsert raced: %s", exc)

    refreshed = (
        supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
    )
    if not refreshed.data:
        raise HTTPException(
            status_code=500,
            detail="Could not initialise preferences row.",
        )
    return refreshed.data[0]


def _log_event(supabase, user_id: str, event: str, properties: dict[str, Any]) -> None:
    """Best-effort analytics write. Never raises."""
    try:
        supabase.table("analytics_events").insert(
            {"event": event, "properties": properties, "user_id": user_id}
        ).execute()
    except Exception as exc:  # pragma: no cover - logging path
        logger.debug("analytics_events insert failed (%s): %s", event, exc)


@router.get("", response_model=JobPreferences)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    row = _get_or_create_row(user_id, supabase)
    return _row_to_model(row)


@router.patch("", response_model=JobPreferences)
async def update_preferences(
    body: JobPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    # Make sure a row exists before we PATCH — the upsert would also
    # work, but a two-step ensures we never accidentally clear a
    # column to its default by sending a partial payload as INSERT.
    existing = _get_or_create_row(user_id, supabase)

    # exclude_unset preserves the "None means don't touch" semantic.
    # exclude_none also keeps a future caller from accidentally NULL-ing
    # a field by sending `null` — frontend should send empty array/dict
    # to clear, not null.
    update: dict[str, Any] = body.model_dump(exclude_unset=True, exclude_none=True)
    if not update:
        # Empty PATCH — degenerate but cheap to handle. Return current
        # state so the client UI stays in sync.
        return _row_to_model(existing)

    # Convert nested Pydantic models to plain dicts for JSONB storage.
    if "languages" in update:
        update["languages"] = [
            lang.model_dump() if hasattr(lang, "model_dump") else lang
            for lang in update["languages"]
        ]
    if "industries" in update:
        update["industries"] = [
            ind.model_dump() if hasattr(ind, "model_dump") else ind
            for ind in update["industries"]
        ]

    # If the user edited target_roles after an auto-populate, the row's
    # source becomes 'mixed' (some user input on top of CV-derived
    # entries). 'user_provided' means we only ever saw user edits;
    # 'cv_inferred' means we only ever saw the auto-populate path.
    if "target_roles" in update:
        prior_source = existing.get("target_roles_source")
        if prior_source == "cv_inferred":
            update["target_roles_source"] = "mixed"
        elif prior_source not in ("mixed",):
            update["target_roles_source"] = "user_provided"

    update["manually_updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_at"] = update["manually_updated_at"]

    supabase.table("user_preferences").update(update).eq("user_id", user_id).execute()

    refreshed = (
        supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
    )
    row = refreshed.data[0] if refreshed.data else existing
    _log_event(
        supabase,
        user_id,
        "preferences_updated",
        {"fields_changed": sorted(k for k in update if k not in ("updated_at", "manually_updated_at"))},
    )
    return _row_to_model(row)
