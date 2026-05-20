"""Ingest classified WhatsApp jobs through the shared jobs pipeline."""
from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import ValidationError

from app.api.v1.jobs import _build_aggregator_blacklist, _ingest_one_job
from app.core.config import get_settings
from app.schemas.jobs import JobCreate
from app.services.job_splitter import split_classification_to_jobs
from app.services.whatsapp_classifier import WhatsappJobClassification
from app.services.whatsapp_scraper import whatsapp_source_for_channel

logger = logging.getLogger(__name__)


def _job_exists_by_whatsapp_id(supabase: Any, message_id: str) -> bool:
    if not message_id:
        return False
    try:
        res = (
            supabase.table("jobs")
            .select("id")
            .eq("whatsapp_message_id", message_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return True
        prefix = f"{message_id}:split:"
        res2 = (
            supabase.table("jobs")
            .select("id")
            .like("whatsapp_message_id", f"{prefix}%")
            .limit(1)
            .execute()
        )
        return bool(res2.data)
    except Exception:
        return False


def classification_to_job_create(
    extracted: WhatsappJobClassification,
    *,
    channel_id: str,
    message_id: str,
    ocr_source_text: Optional[str] = None,
) -> JobCreate:
    """Map classifier output to JobCreate for _ingest_one_job."""
    desc = (extracted.description or "").strip()
    if len(desc) < 20:
        desc = (
            f"{extracted.title or 'Role'} at {extracted.company or 'Company'}. "
            f"{desc}"
        ).strip()[:8000]
    return JobCreate(
        title=(extracted.title or "Untitled role")[:500],
        company=extracted.company,
        location=extracted.location,
        description=desc,
        requirements=extracted.qualifications_required or [],
        skills_required=extracted.skills or [],
        apply_url=extracted.apply_url,
        apply_email=extracted.apply_email,
        source=whatsapp_source_for_channel(channel_id),
        source_url=f"whatsapp://channel/{channel_id}/{message_id}",
        employment_type=extracted.employment_type,
        work_arrangement=extracted.work_arrangement,
        experience_min_years=extracted.experience_min_years,
        seniority_level=extracted.seniority_level,
        qualifications_required=extracted.qualifications_required or [],
        whatsapp_message_id=message_id,
        ocr_source_text=ocr_source_text or extracted.ocr_text,
    )


async def ingest_whatsapp_classification(
    supabase: Any,
    extracted: WhatsappJobClassification,
    *,
    channel_id: str,
    message_id: str,
    message_body: str = "",
    ocr_source_text: Optional[str] = None,
) -> dict[str, Any]:
    """Run dedup checks and _ingest_one_job (possibly split into N jobs)."""
    if not extracted.is_job:
        return {"status": "not_a_job"}

    if _job_exists_by_whatsapp_id(supabase, message_id):
        return {"status": "duplicate_message_id"}

    try:
        base_job = classification_to_job_create(
            extracted,
            channel_id=channel_id,
            message_id=message_id,
            ocr_source_text=ocr_source_text,
        )
        job_creates = await split_classification_to_jobs(
            message_body,
            extracted,
            base_job,
            message_id=message_id,
            supabase=supabase,
        )
    except ValidationError as ve:
        logger.warning("WhatsApp job validation failed: %s", ve.errors()[:2])
        return {"status": "validation_failed"}

    settings = get_settings()
    blacklist = _build_aggregator_blacklist(settings)
    ingested = 0
    duplicates = 0
    errors = 0
    titles: list[str] = []

    for job_create in job_creates:
        result, detail = await _ingest_one_job(supabase, job_create, blacklist)
        if result == "ingested":
            ingested += 1
            titles.append(job_create.title)
        elif result == "duplicate":
            duplicates += 1
        else:
            errors += 1
            logger.info(
                "WhatsApp split ingest %s for %r: %s",
                result,
                job_create.title,
                detail,
            )

    if ingested == 0:
        if duplicates > 0 and errors == 0:
            return {"status": "ok", "ingest_result": "duplicate"}
        return {"status": "validation_failed" if errors else "not_ingested"}

    return {
        "status": "ok",
        "ingest_result": "ingested",
        "ingested_count": ingested,
        "split_count": len(job_creates),
        "titles": titles,
        "title": titles[0] if titles else base_job.title,
    }
