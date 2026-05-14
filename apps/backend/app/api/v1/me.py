"""Data-subject-rights endpoints (task #63).

Implements the Zambia Data Protection Act 2021 + GDPR-aligned rights of
access (GET /api/v1/me/export) and erasure (DELETE /api/v1/me). Kept
in its own router file — distinct from /profile — so the audit log
clearly separates self-care reads/updates from rights exercise.
"""
from __future__ import annotations

import hmac
import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.deps import get_current_user_id, get_supabase
from app.core.rate_limit import limiter
from app.schemas.me import AccountDeletionRequest, AccountDeletionResult

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["DataRights"])


# ── rate-limit key: per user, not per IP ──
# The data export is bounded "1/hour per user" by spec. The shared
# slowapi limiter uses get_remote_address by default, which would let
# someone on a shared NAT exhaust the limit for an unrelated user. We
# pull the JWT.sub instead so the bucket is keyed to the authenticated
# user; fall back to IP only if the token can't be decoded (which on
# this authenticated route is also caught by Depends(get_current_user_id),
# so the fallback is purely defence-in-depth).
def _per_user_key(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass
    return get_remote_address(request)


# ───────────────────────────── EXPORT ─────────────────────────────

# Internal columns that must never leave the server. cvs.embedding is a
# 768-dim vector — useless to the user, expensive to serialise, and
# leaks model details if surfaced.
_CV_EXPORT_COLUMNS = "id, file_type, raw_text, parsed_data, parsing_confidence, is_primary, created_at"


def _build_export_bundle(user_id: str, supabase) -> dict[str, Any]:
    """Assemble the full data bundle. Pure I/O — easy to unit test."""

    # 1. Profile row (also gives us preferences, which live as columns
    #    on the users table per migration 002).
    user_row = (
        supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_row.data[0]

    # 2. Subscription history + payments. Both are time-ordered so the
    #    export reads as a ledger.
    subscriptions = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )
    payments = (
        supabase.table("payments")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )

    # 3. CVs — explicitly exclude `embedding` (internal, vector). raw_text
    #    + parsed_data IS in scope per the task spec.
    cvs = (
        supabase.table("cvs")
        .select(_CV_EXPORT_COLUMNS)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )

    # 4. Generated CVs (cv_generations) — user-tailored AI output, owned
    #    by the user. Includes the prompt/job context in `metadata`.
    cv_generations = (
        supabase.table("cv_generations")
        .select("id, job_title, company, content, word_count, metadata, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )

    # 5. Matches WITH job snapshots at the time. We pull the live job
    #    row alongside each match — the matches table doesn't carry a
    #    historical snapshot, so this is "as of export time" rather than
    #    "as of match time". That's the most accurate snapshot we have
    #    without changing the matches schema.
    match_rows = (
        supabase.table("matches")
        .select(
            "id, job_id, cv_id, score, vector_score, skill_score, bonus_score, "
            "matched_skills, missing_skills, explanation, status, created_at"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )
    job_ids = [m["job_id"] for m in match_rows if m.get("job_id")]
    job_snapshots: dict[str, dict] = {}
    if job_ids:
        # Same selection as the user can see today — no internal-only
        # columns like `embedding` or `quality_score` raw weighting.
        job_rows = (
            supabase.table("jobs")
            .select(
                "id, title, company, location, description, requirements, "
                "salary_min, salary_max, apply_url, apply_email, source, "
                "source_url, closing_date, posted_at"
            )
            .in_("id", job_ids)
            .execute()
            .data
            or []
        )
        job_snapshots = {row["id"]: row for row in job_rows}
    matches = [
        {**m, "job_snapshot": job_snapshots.get(m.get("job_id"))} for m in match_rows
    ]

    # 6. user_skills with canonical skill names attached.
    user_skill_rows = (
        supabase.table("user_skills")
        .select("proficiency, source, skills(name)")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    user_skills = [
        {
            "name": (r.get("skills") or {}).get("name"),
            "proficiency": r.get("proficiency"),
            "source": r.get("source"),
        }
        for r in user_skill_rows
        if (r.get("skills") or {}).get("name")
    ]

    # 7. Preferences live as columns on `users` — surface them as their
    #    own block so the export reads cleanly without forcing the user
    #    to find them inside the profile dump.
    preferences = {
        "whatsapp_alerts": user.get("whatsapp_alerts"),
        "email_notifications_enabled": user.get("email_notifications_enabled"),
        "language": user.get("language"),
    }

    return {
        "export_format_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "data_controller": "Vergeo (ZedApply), Lusaka, Zambia",
        "rights_basis": (
            "Zambia Data Protection Act 2021 — right of access (Article 23). "
            "See /legal/privacy for the full notice."
        ),
        "profile": user,
        "preferences": preferences,
        "subscriptions": subscriptions,
        "payments": payments,
        "cvs": cvs,
        "cv_generations": cv_generations,
        "matches": matches,
        "user_skills": user_skills,
    }


@router.get("/export")
@limiter.limit("1/hour", key_func=_per_user_key)
async def export_my_data(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Stream the user's full data bundle as a JSON download.

    Rate-limited 1/hour per authenticated user. Returns 429 on overrun.
    """
    bundle = _build_export_bundle(user_id, supabase)
    # json.dumps with default=str so datetimes/UUIDs serialise cleanly.
    body = json.dumps(bundle, ensure_ascii=False, indent=2, default=str)
    filename = f"zedcv-data-export-{date.today().isoformat()}.json"

    def _iter() -> Any:
        # Yielding in a single chunk is fine — even a power user with
        # hundreds of matches comes out under a few MB. Kept as a
        # generator so we use StreamingResponse semantics (no buffering
        # of the full body in the framework's response object).
        yield body

    return StreamingResponse(
        _iter(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Format-Version": "1.0",
            "Cache-Control": "no-store",
        },
    )


# ──────────────────────────── DELETE ────────────────────────────


def _purge_cv_storage(user_id: str, supabase) -> int:
    """Best-effort: remove all CV files under cvs/{user_id}/* in storage.

    Returns the count of files removed. Storage exceptions are logged
    and swallowed — losing a few orphaned bytes in storage is far
    preferable to a partial delete that leaves the DB row intact.
    """
    bucket = "documents"
    prefix = f"cvs/{user_id}"
    try:
        listing = supabase.storage.from_(bucket).list(prefix)
    except Exception as exc:  # noqa: BLE001
        log.warning("storage list failed for %s: %s", prefix, exc)
        return 0

    if not listing:
        return 0

    paths = [f"{prefix}/{f['name']}" for f in listing if isinstance(f, dict) and f.get("name")]
    if not paths:
        return 0

    try:
        supabase.storage.from_(bucket).remove(paths)
    except Exception as exc:  # noqa: BLE001
        log.warning("storage remove failed for %d paths under %s: %s", len(paths), prefix, exc)
        return 0
    return len(paths)


@router.delete("", response_model=AccountDeletionResult)
async def delete_my_account(
    body: AccountDeletionRequest,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Hard-delete the caller's account.

    Confirmation: the body's `confirm_phone` must match the user's
    stored phone byte-for-byte. The match is a `hmac.compare_digest`
    on the raw bytes — no LLM, no normalisation, no parsing.

    Idempotent: a second call with a valid JWT after the user is gone
    returns 200 with `already_deleted=true` so the frontend doesn't
    have to special-case it.

    Cascade behaviour (FK-driven, NOT application-side):
      - user_skills, cvs, cv_generations, matches, generated_documents,
        application_outcomes, cv_upload_queue: ON DELETE CASCADE.
      - subscriptions, payments: ON DELETE SET NULL (migration 018) —
        the row is retained for 7 years per Zambian tax law.
      - whatsapp_sessions: ON DELETE SET NULL (already in 001).

    What this endpoint does on top of the cascade:
      - Removes the user's CV files from Supabase storage.
      - Deletes otp_codes rows matching the phone (no FK link, so the
        cascade doesn't reach them).
    """

    # Look up the user. Idempotent path: token still valid, user gone.
    existing = (
        supabase.table("users")
        .select("id, phone")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return AccountDeletionResult(deleted=False, already_deleted=True, user_id=None)

    user_row = existing.data[0]
    stored_phone: Optional[str] = user_row.get("phone")
    if not stored_phone:
        # Bizarre data state — refuse to delete without a phone to confirm.
        raise HTTPException(status_code=500, detail="Account is missing a phone of record")

    # Bytes-exact constant-time compare. NEVER pass either side through
    # any LLM, normaliser, or parser — a single normalised whitespace
    # would silently widen the confirmation to a class of inputs.
    if not hmac.compare_digest(
        body.confirm_phone.encode("utf-8"),
        stored_phone.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmation phone does not match. Type the phone "
                "number on your account exactly, including the +260 prefix."
            ),
        )

    # Storage purge first — if it fails we still want to proceed (the
    # function logs and swallows), but ordering it first means a hard
    # storage outage doesn't leave a deleted DB user with orphan files
    # for too long. The cascade comes next.
    _purge_cv_storage(user_id, supabase)

    # Trigger the FK cascade. After this returns, the user is gone and
    # subscriptions/payments are anonymised (migration 018).
    supabase.table("users").delete().eq("id", user_id).execute()

    # OTPs aren't linked by FK (phone-keyed). Best-effort sweep so a
    # post-deletion OTP request doesn't find stale rows under the same
    # phone if the same person ever re-registers.
    try:
        supabase.table("otp_codes").delete().eq("phone", stored_phone).execute()
    except Exception as exc:  # noqa: BLE001
        log.warning("otp_codes sweep failed for %s: %s", stored_phone, exc)

    log.info("data-rights deletion completed for user_id=%s", user_id)
    return AccountDeletionResult(deleted=True, already_deleted=False, user_id=user_id)
