"""Portable data export (ZDPA right-to-portability, Bucket 9)."""
from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.config import Settings
from app.services.otp import verify_sensitive_action_otp
from app.services.storage import download_storage_object, upload_export_zip

log = logging.getLogger(__name__)

_CV_EXPORT_COLUMNS = (
    "id, file_url, file_type, raw_text, parsed_data, parsing_confidence, "
    "is_primary, created_at"
)


def request_export(
    user_id: str,
    *,
    otp_code: str,
    supabase: Any,
    settings: Settings,
) -> dict[str, Any]:
    user_row = (
        supabase.table("users")
        .select("id, phone, deleted_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_row.data[0]
    if user.get("deleted_at"):
        raise HTTPException(status_code=409, detail="Account already deleted")

    phone = user.get("phone")
    if not phone:
        raise HTTPException(status_code=500, detail="Account is missing a phone of record")

    verify_sensitive_action_otp(
        user_phone=phone,
        otp_code=otp_code,
        action="export_data",
        supabase=supabase,
        settings=settings,
    )

    active = (
        supabase.table("data_export_requests")
        .select("id, status")
        .eq("user_id", user_id)
        .in_("status", ["pending", "generating"])
        .limit(1)
        .execute()
    )
    if active.data:
        row = active.data[0]
        return {"request_id": row["id"], "status": row["status"]}

    inserted = (
        supabase.table("data_export_requests")
        .insert({"user_id": user_id, "status": "pending"})
        .execute()
    )
    row = inserted.data[0] if inserted.data else {}
    return {"request_id": row.get("id"), "status": "pending"}


def _build_profile_bundle(user_id: str, supabase: Any) -> dict[str, Any]:
    user = (
        supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    )
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    def _rows(table: str, select: str = "*", order: str = "created_at") -> list:
        return (
            supabase.table(table)
            .select(select)
            .eq("user_id", user_id)
            .order(order, desc=False)
            .execute()
            .data
            or []
        )

    match_rows = _rows(
        "matches",
        "id, job_id, cv_id, score, vector_score, skill_score, bonus_score, "
        "matched_skills, missing_skills, explanation, status, created_at",
    )
    job_ids = [m["job_id"] for m in match_rows if m.get("job_id")]
    job_snapshots: dict[str, dict] = {}
    if job_ids:
        jobs = (
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
        job_snapshots = {j["id"]: j for j in jobs}

    skill_rows = _rows("user_skills", "proficiency, source, skills(name)")
    user_skills = [
        {
            "name": (r.get("skills") or {}).get("name"),
            "proficiency": r.get("proficiency"),
            "source": r.get("source"),
        }
        for r in skill_rows
        if (r.get("skills") or {}).get("name")
    ]

    return {
        "export_format_version": "2.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": user.data[0],
        "subscriptions": _rows("subscriptions"),
        "payments": _rows("payments"),
        "cvs": _rows("cvs", _CV_EXPORT_COLUMNS),
        "cv_generations": _rows(
            "cv_generations",
            "id, job_title, company, content, word_count, metadata, created_at",
        ),
        "matches": [
            {**m, "job_snapshot": job_snapshots.get(m.get("job_id"))}
            for m in match_rows
        ],
        "user_skills": user_skills,
        "user_preferences": _rows("user_preferences"),
        "consent_log": _rows("consent_log"),
        "interview_sessions": _rows("interview_sessions"),
        "aptitude_scores": _rows("aptitude_scores"),
        "application_outcomes": _rows("application_outcomes"),
        "generated_documents": _rows("generated_documents"),
        "saved_jobs": _rows("saved_jobs", "job_id, created_at"),
    }


def _matches_csv(matches: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    fields = [
        "id",
        "job_id",
        "score",
        "status",
        "matched_skills",
        "missing_skills",
        "explanation",
        "created_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in matches:
        flat = dict(row)
        for key in ("matched_skills", "missing_skills"):
            if isinstance(flat.get(key), list):
                flat[key] = ";".join(str(x) for x in flat[key])
        writer.writerow(flat)
    return buf.getvalue()


def generate_export(request_id: str, supabase: Any) -> dict[str, Any]:
    """Build ZIP, upload to storage, mark request ready."""
    req = (
        supabase.table("data_export_requests")
        .select("id, user_id, status")
        .eq("id", request_id)
        .limit(1)
        .execute()
    )
    if not req.data:
        raise HTTPException(status_code=404, detail="Export request not found")
    row = req.data[0]
    if row.get("status") not in ("pending", "generating"):
        raise HTTPException(
            status_code=400,
            detail=f"Export not generatable (status={row.get('status')})",
        )

    user_id = row["user_id"]
    supabase.table("data_export_requests").update({
        "status": "generating",
    }).eq("id", request_id).execute()

    bundle = _build_profile_bundle(user_id, supabase)
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "profile.json",
            json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        )
        zf.writestr(
            "consent_log.json",
            json.dumps(bundle.get("consent_log", []), default=str, indent=2),
        )
        zf.writestr("matches.csv", _matches_csv(bundle.get("matches", [])))

        for cv in bundle.get("cvs", []):
            path = cv.get("file_url")
            if not path or not isinstance(path, str):
                continue
            blob = download_storage_object(path, supabase)
            if blob:
                name = path.split("/")[-1] or f"{cv.get('id', 'cv')}.bin"
                zf.writestr(f"cvs/{name}", blob)

    url, expires_at = upload_export_zip(
        user_id, request_id, zip_buf.getvalue(), supabase
    )
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("data_export_requests").update({
        "status": "ready",
        "generated_at": now,
        "download_url": url,
        "download_expires_at": expires_at,
        "failure_reason": None,
    }).eq("id", request_id).execute()

    return {
        "request_id": request_id,
        "status": "ready",
        "download_url": url,
        "download_expires_at": expires_at,
    }


def get_export_status(user_id: str, request_id: str, supabase: Any) -> dict[str, Any]:
    result = (
        supabase.table("data_export_requests")
        .select(
            "id, status, download_url, download_expires_at, generated_at, failure_reason"
        )
        .eq("id", request_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Export request not found")
    row = result.data[0]
    if (
        row.get("status") == "ready"
        and row.get("download_expires_at")
        and row["download_expires_at"] < datetime.now(timezone.utc).isoformat()
    ):
        supabase.table("data_export_requests").update({
            "status": "expired",
        }).eq("id", request_id).execute()
        row["status"] = "expired"
    return {
        "request_id": row["id"],
        "status": row.get("status"),
        "download_url": row.get("download_url"),
        "download_expires_at": row.get("download_expires_at"),
        "generated_at": row.get("generated_at"),
        "failure_reason": row.get("failure_reason"),
    }
