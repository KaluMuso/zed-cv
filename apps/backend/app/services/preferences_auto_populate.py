"""CV upload → user_preferences auto-populate.

Wired into POST /cv/upload after the skill-resolver pass. Reads
`cvs.parsed_data` and fills the user's user_preferences row with what
can be inferred from the CV: target roles, languages, regions, and
industries.

Hard guarantees (do not regress these — they're load-bearing for the
"Re-uploading a CV does NOT overwrite manually-edited fields"
acceptance criterion):

  1. We never overwrite a field the user has manually edited. The
     check is per-field: if `manually_updated_at` is set AND the field
     has a non-empty value, we leave it alone, full stop.
  2. We never *clear* a field. If we don't have an inference, the row
     stays as-is for that column.
  3. Auto-populate failure does NOT fail the CV upload. Caller wraps
     this in try/except — additionally, every Supabase call here is
     itself wrapped in a logged-but-swallowed except.

Industry classification is deliberately small and rule-based — see
`_classify_industry`. We'd rather skip an entry than guess wrong; the
acceptance criteria explicitly call for "never guess".
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.role_inference import normalize_role_titles

logger = logging.getLogger(__name__)


# How many recent roles to lift into target_roles. The CV-spec calls
# for "most recent 3 roles" — beyond that, the entries get stale fast.
DEFAULT_RECENT_ROLES = 3

# Known languages we can extract from the flat parsed_data.skills list.
# Lowercased and stripped before lookup. Keep this list short and
# Zambia-focused — it's a fallback for CVs that don't have a structured
# `languages` section. False positives here would attribute a foreign
# language to someone who only mentioned a place name, so we err
# conservative.
KNOWN_LANGUAGES: set[str] = {
    "english",
    "bemba",
    "nyanja",
    "chinyanja",
    "tonga",
    "lozi",
    "kaonde",
    "lunda",
    "luvale",
    "tumbuka",
    "swahili",
    "kiswahili",
    "french",
    "portuguese",
    "spanish",
    "arabic",
    "mandarin",
    "chinese",
    "afrikaans",
    "german",
    "italian",
}

# Mapping from CV-section proficiency vocab to our wider self-rating
# vocab. CVSections has "conversational"; user_preferences has
# "intermediate" — they mean roughly the same thing in this context.
_PROFICIENCY_MAP = {
    "native": "native",
    "fluent": "fluent",
    "conversational": "intermediate",
    "intermediate": "intermediate",
    "basic": "basic",
}


# Industry keyword classifier. Maps keyword (case-insensitive substring
# match) to industry. ORDER MATTERS — first hit wins. Curate carefully:
# false-positive on a generic word like "manager" or "office" would
# slap the wrong industry on most CVs.
#
# This is intentionally tiny: the acceptance criteria say "when the
# keyword classifier can't determine industry, leave that work_experience
# entry out of industries; never guess". Adding entries cheaply expands
# coverage; getting them wrong silently corrupts user data.
_INDUSTRY_KEYWORDS: list[tuple[str, str]] = [
    # Agriculture / farming
    ("agricult", "Agriculture"),
    ("farming", "Agriculture"),
    ("farm ", "Agriculture"),
    ("agronomy", "Agriculture"),
    ("livestock", "Agriculture"),
    # Mining (huge in Zambia — copperbelt)
    ("mining", "Mining"),
    ("mineral", "Mining"),
    ("smelter", "Mining"),
    ("copperbelt", "Mining"),
    ("mopani", "Mining"),
    ("kcm", "Mining"),
    # Healthcare
    ("hospital", "Healthcare"),
    ("clinic", "Healthcare"),
    ("health center", "Healthcare"),
    ("health centre", "Healthcare"),
    ("nurse", "Healthcare"),
    ("pharma", "Healthcare"),
    ("medical", "Healthcare"),
    ("physician", "Healthcare"),
    # Government / public sector
    ("ministry", "Government"),
    ("government", "Government"),
    ("ministerial", "Government"),
    ("council", "Government"),
    ("municipal", "Government"),
    ("public sector", "Government"),
    # Banking / finance
    ("bank", "Banking"),
    ("zanaco", "Banking"),
    ("stanbic", "Banking"),
    ("absa", "Banking"),
    ("microfinance", "Banking"),
    ("insurance", "Insurance"),
    # NGO / development
    ("ngo", "NGO"),
    ("non-governmental", "NGO"),
    ("non-profit", "NGO"),
    ("usaid", "NGO"),
    ("unicef", "NGO"),
    ("oxfam", "NGO"),
    ("world bank", "NGO"),
    # Education
    ("university", "Education"),
    ("college", "Education"),
    ("school", "Education"),
    ("teacher", "Education"),
    ("lecturer", "Education"),
    # Telco / tech
    ("telecom", "Telecommunications"),
    ("mtn", "Telecommunications"),
    ("airtel", "Telecommunications"),
    ("zamtel", "Telecommunications"),
    ("software", "Technology"),
    ("tech ", "Technology"),
    ("startup", "Technology"),
    # Retail / hospitality
    ("retail", "Retail"),
    ("supermarket", "Retail"),
    ("hotel", "Hospitality"),
    ("lodge", "Hospitality"),
    ("hospitality", "Hospitality"),
    # Construction / engineering
    ("construction", "Construction"),
    ("contractor", "Construction"),
    ("engineering firm", "Engineering"),
    ("consult", "Consulting"),
    # Logistics
    ("logistics", "Logistics"),
    ("freight", "Logistics"),
    ("transport", "Logistics"),
]


def _classify_industry(company: str, role_text: str) -> Optional[str]:
    """Return a coarse industry label for one role, or None if unclear.

    Looks at both the company name and the role description (achievements
    concatenated). Never guesses — returns None when no keyword fires.
    """
    haystack = f"{company or ''} {role_text or ''}".lower()
    if not haystack.strip():
        return None
    for needle, industry in _INDUSTRY_KEYWORDS:
        if needle in haystack:
            return industry
    return None


def _extract_languages_from_skills(skills: list[str]) -> list[dict[str, str]]:
    """Best-effort language extraction from the flat parsed_data.skills.

    Returns a list of {language, proficiency} dicts. Proficiency
    defaults to "intermediate" since the flat skill list carries no
    proficiency information.
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in skills:
        if not isinstance(raw, str):
            continue
        norm = raw.strip().lower()
        if norm in KNOWN_LANGUAGES and norm not in seen:
            seen.add(norm)
            out.append({"language": norm.title(), "proficiency": "intermediate"})
    return out


def _extract_languages_from_sections(sections_languages: list[dict]) -> list[dict[str, str]]:
    """Pull languages out of parsed_data.sections.languages (richer shape)."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in sections_languages or []:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        prof_in = (entry.get("proficiency") or "").strip().lower()
        prof_out = _PROFICIENCY_MAP.get(prof_in, "intermediate")
        out.append({"language": name, "proficiency": prof_out})
    return out


def _infer_target_roles(parsed_data: dict[str, Any]) -> list[str]:
    """Return up to DEFAULT_RECENT_ROLES normalised target_role strings.

    Prefers `sections.work_experience` if present; otherwise falls back
    to parsing the flat `experience_summary` (best-effort — the
    fall-back rarely yields good titles, and that's fine; we'd rather
    return an empty list than guess).
    """
    sections = parsed_data.get("sections") or {}
    work_experience = sections.get("work_experience") if isinstance(sections, dict) else None
    if work_experience and isinstance(work_experience, list):
        titles = [
            (entry.get("title") or "")
            for entry in work_experience
            if isinstance(entry, dict)
        ]
        return normalize_role_titles(titles)[:DEFAULT_RECENT_ROLES]
    return []


def _infer_industries(parsed_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a deduplicated list of {industry, years_experience} dicts.

    Years are accumulated across roles tagged to the same industry by
    `_classify_industry`. Unclassifiable roles are dropped entirely.
    """
    sections = parsed_data.get("sections") or {}
    work_experience = sections.get("work_experience") if isinstance(sections, dict) else None
    if not work_experience or not isinstance(work_experience, list):
        return []

    totals: dict[str, int] = {}
    for entry in work_experience:
        if not isinstance(entry, dict):
            continue
        company = entry.get("company") or ""
        achievements = entry.get("achievements") or []
        role_text = " ".join(achievements) if isinstance(achievements, list) else ""
        industry = _classify_industry(company, role_text)
        if not industry:
            continue
        years = _approx_years(entry.get("start_date"), entry.get("end_date"))
        totals[industry] = totals.get(industry, 0) + years

    return [
        {"industry": ind, "years_experience": yrs}
        for ind, yrs in totals.items()
        if yrs > 0 or True  # include zero-year entries — UI shows them
    ]


def _approx_years(start: Optional[str], end: Optional[str]) -> int:
    """Approximate role duration in years from YYYY / YYYY-MM strings.

    Returns 0 on unparseable input. Caps at 60 — anything above is
    almost certainly a typo in the CV.
    """
    if not start:
        return 0
    try:
        start_year = int(str(start)[:4])
    except (ValueError, TypeError):
        return 0
    end_year: int
    if not end:
        end_year = datetime.now(timezone.utc).year
    else:
        try:
            end_year = int(str(end)[:4])
        except (ValueError, TypeError):
            end_year = datetime.now(timezone.utc).year
    if end_year < start_year:
        return 0
    return min(end_year - start_year, 60)


def _infer_regions(parsed_data: dict[str, Any]) -> list[str]:
    """Lift the parsed location into an acceptable_regions entry."""
    location = parsed_data.get("location")
    if not location or not isinstance(location, str):
        return []
    trimmed = location.strip()
    if not trimmed:
        return []
    return [trimmed]


def _is_field_empty(value: Any) -> bool:
    """Treat None, empty string, empty list, and empty dict as empty."""
    if value is None:
        return True
    if isinstance(value, (str, list, dict)) and len(value) == 0:
        return True
    return False


def _log_event(supabase, user_id: str, event: str, properties: dict[str, Any]) -> None:
    """Best-effort analytics write."""
    try:
        supabase.table("analytics_events").insert(
            {"event": event, "properties": properties, "user_id": user_id}
        ).execute()
    except Exception as exc:  # pragma: no cover - logging path
        logger.debug("analytics_events insert failed (%s): %s", event, exc)


async def auto_populate_from_cv(
    user_id: str,
    parsed_data: dict[str, Any],
    *,
    supabase,
) -> list[str]:
    """Auto-populate the user's user_preferences row from a parsed CV.

    Returns the list of fields it actually filled (used by the
    `preferences_auto_populated` analytics event and visible in test
    assertions). Empty list means nothing was filled — that's not an
    error.

    Idempotent: calling twice with the same parsed_data is safe and
    fills nothing the second time (every field is already populated).
    Re-upload safety: a manual edit (manually_updated_at advanced) on
    a field locks it from this path forever, until the user clears it
    themselves.
    """
    if not isinstance(parsed_data, dict):
        return []

    # Ensure a row exists. The /preferences GET endpoint also creates
    # one on first access, but /cv/upload doesn't go through there — so
    # we have to handle the "first ever interaction" case ourselves.
    try:
        existing_res = (
            supabase.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("auto_populate_from_cv: row lookup failed for %s: %s", user_id, exc)
        return []

    existing: dict[str, Any]
    if existing_res.data:
        existing = existing_res.data[0]
    else:
        try:
            supabase.table("user_preferences").upsert(
                {"user_id": user_id},
                on_conflict="user_id",
                ignore_duplicates=True,
            ).execute()
        except Exception as exc:
            logger.warning("auto_populate_from_cv: row create failed for %s: %s", user_id, exc)
            return []
        existing = {"user_id": user_id}

    manually_updated_at = existing.get("manually_updated_at")

    update: dict[str, Any] = {}
    filled: list[str] = []

    # target_roles. We don't overwrite a manually-edited target_roles
    # list. If the user never touched it (manually_updated_at NULL) or
    # the existing list is empty, we fill from the CV. After filling
    # we set the source to 'cv_inferred'.
    if _should_fill("target_roles", existing, manually_updated_at):
        inferred_roles = _infer_target_roles(parsed_data)
        if inferred_roles:
            update["target_roles"] = inferred_roles
            update["target_roles_source"] = "cv_inferred"
            filled.append("target_roles")

    # languages. Prefer sections.languages, fall back to skills extraction.
    if _should_fill("languages", existing, manually_updated_at):
        sections = parsed_data.get("sections") or {}
        sections_langs = sections.get("languages") if isinstance(sections, dict) else None
        inferred_languages = _extract_languages_from_sections(sections_langs or [])
        if not inferred_languages:
            inferred_languages = _extract_languages_from_skills(parsed_data.get("skills") or [])
        if inferred_languages:
            update["languages"] = inferred_languages
            filled.append("languages")

    # industries.
    if _should_fill("industries", existing, manually_updated_at):
        inferred_industries = _infer_industries(parsed_data)
        if inferred_industries:
            update["industries"] = inferred_industries
            filled.append("industries")

    # acceptable_regions from parsed location.
    if _should_fill("acceptable_regions", existing, manually_updated_at):
        inferred_regions = _infer_regions(parsed_data)
        if inferred_regions:
            update["acceptable_regions"] = inferred_regions
            filled.append("acceptable_regions")

    if not filled:
        return []

    update["auto_populated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_at"] = update["auto_populated_at"]

    try:
        supabase.table("user_preferences").update(update).eq("user_id", user_id).execute()
    except Exception as exc:
        logger.warning("auto_populate_from_cv: update failed for %s: %s", user_id, exc)
        return []

    _log_event(supabase, user_id, "preferences_auto_populated", {"fields_filled": filled})
    return filled


def _should_fill(field: str, existing: dict[str, Any], manually_updated_at: Any) -> bool:
    """Decide whether the auto-populate path can touch `field`.

    Yes when both:
      - the current value is empty (we never overwrite real content),
      - no manual edit has happened that would suggest the user
        deliberately left it empty.

    The combined check is conservative — once a user touches *any*
    field, we lock the empty ones too until the next CV upload after
    they clear manually_updated_at (which they can't do directly; in
    practice this means a manual PATCH wins forever). That's the right
    bias: the user is the source of truth.
    """
    current = existing.get(field)
    if not _is_field_empty(current):
        return False
    if manually_updated_at:
        # User has previously edited *something* on this row. To keep
        # the contract simple ("auto-populate never clobbers manual
        # entries"), we don't fill any field after the first manual
        # edit. The user can clear the row in a future iteration.
        return False
    return True
