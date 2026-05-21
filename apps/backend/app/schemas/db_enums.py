"""App-layer enums that replace dropped SQL CHECK constraints.

Migration 013 drops the CHECK constraints on `ai_cache.cache_type` and
`cv_upload_queue.status` (plus the tier columns, which already had a
matching `SubscriptionTier` enum in `subscription.py`). These enums are
now the single source of truth for what values are allowed in those
columns; every write site goes through `validate_*` helpers so an
invalid value raises at the app boundary instead of silently landing
in the DB.

Pattern for the helpers: accept a string, return the string only if
it's a valid enum member, raise ValueError otherwise. This is a
lighter-weight pattern than wrapping every insert dict in a Pydantic
model — fits the existing `supabase.table(...).insert(dict)` style at
the call sites in `cv.py`, `interview_prep.py`, and `admin.py`.

When adding a new value, edit ONLY this file. No migration needed.
"""
from enum import Enum


class CacheType(str, Enum):
    """Allowed values for ai_cache.cache_type.

    The CHECK that used to enforce this was widened three times across
    migrations 004, 005, 011 — adding `cv_analysis` and `interview_prep`
    each required a separate prod migration. Now the source of truth is
    here. Adding a new cache flavour = one PR, no DB change.
    """
    embedding = "embedding"
    cv_parse = "cv_parse"
    cv_analysis = "cv_analysis"        # cv.py /analyze
    cover_letter = "cover_letter"      # cover_letter.py /generate
    interview_prep = "interview_prep"  # interview_prep.py /generate
    explanation = "explanation"        # matches.py /explain
    job_extract = "job_extract"        # job_extractor.py — WhatsApp channel ingest
    whatsapp_classify = "whatsapp_classify"  # whatsapp_classifier.py — Track 4c
    whatsapp_split = "whatsapp_split"        # job_splitter.py — Track 4d
    admin_alert = "admin_alert"              # admin_alerts.py — ops WhatsApp alerts


class QueueStatus(str, Enum):
    """Allowed values for cv_upload_queue.status.

    State machine:
        queued      → drain_cv_queue picks it up
        processing  → in-flight inside drain_cv_queue
        completed   → finalized, row stays for audit
        failed      → attempts exceeded retry limit
    """
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


def validate_cache_type(value: str) -> str:
    """Return `value` if it's a known CacheType, else raise ValueError.

    Use at every `ai_cache.insert()` call site so an unknown cache_type
    fails at the app layer rather than silently writing bad data now
    that the SQL CHECK is gone.
    """
    try:
        return CacheType(value).value
    except ValueError as exc:
        raise ValueError(
            f"Unknown cache_type {value!r}. Allowed: "
            f"{[m.value for m in CacheType]}"
        ) from exc


def validate_queue_status(value: str) -> str:
    """Return `value` if it's a known QueueStatus, else raise ValueError."""
    try:
        return QueueStatus(value).value
    except ValueError as exc:
        raise ValueError(
            f"Unknown queue status {value!r}. Allowed: "
            f"{[m.value for m in QueueStatus]}"
        ) from exc
