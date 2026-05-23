"""Persist deep-link enrichment results onto job rows."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.deep_link_parsers import EnrichmentResult
from app.services.deep_link_router import detect_parser_name
from app.services.deep_link_telemetry import record_parser_telemetry

logger = logging.getLogger(__name__)


def job_needs_enrichment(row: dict) -> bool:
    """Skip when apply fields populated or enrichment already attempted."""
    if row.get("apply_url") or row.get("apply_email"):
        return False
    if not row.get("source_url"):
        return False
    if row.get("enrichment_attempted_at"):
        return False
    return True


def _apply_enrichment_patch(
    row: dict,
    result: EnrichmentResult,
    patch: dict[str, Any],
) -> bool:
    updated = False
    if result.apply_email and not row.get("apply_email"):
        patch["apply_email"] = result.apply_email
        patch["apply_source"] = "enriched"
        updated = True
    elif result.apply_url and not row.get("apply_url"):
        patch["apply_url"] = result.apply_url
        patch["apply_source"] = "enriched"
        updated = True
    if result.contact_phone and not row.get("contact_phone"):
        patch["contact_phone"] = result.contact_phone
        updated = True
    return updated


async def enrich_job_row(supabase: Any, job_id: str, row: dict) -> bool:
    """Fetch source_url + description body, update jobs.apply_* when found."""
    working = dict(row)
    from app.services.description_body_extractor import merge_description_extraction

    merge_description_extraction(working, working.get("description"))

    if not job_needs_enrichment(working) and not (
        working.get("apply_url") or working.get("apply_email")
    ):
        return False

    patch_desc: dict[str, Any] = {}
    if working.get("apply_email") and not row.get("apply_email"):
        patch_desc["apply_email"] = working["apply_email"]
        patch_desc["apply_source"] = working.get("apply_source") or "description_email"
    elif working.get("apply_url") and not row.get("apply_url"):
        patch_desc["apply_url"] = working["apply_url"]
        patch_desc["apply_source"] = working.get("apply_source") or "description_url"
    if working.get("contact_phone") and not row.get("contact_phone"):
        patch_desc["contact_phone"] = working["contact_phone"]
    if patch_desc:
        supabase.table("jobs").update(patch_desc).eq("id", job_id).execute()
        row.update(patch_desc)

    if not job_needs_enrichment(row):
        return bool(patch_desc)

    source_url = str(row.get("source_url") or "")
    now = datetime.now(timezone.utc).isoformat()
    patch: dict[str, Any] = {"enrichment_attempted_at": now}

    try:
        from app.services.deep_link_enricher import enrich_from_source_url

        result = await enrich_from_source_url(source_url)
    except Exception as exc:
        logger.warning("enrich_job_row %s failed: %s", job_id, exc)
        record_parser_telemetry(
            supabase,
            job_id=job_id,
            source_url=source_url,
            result=EnrichmentResult(parser=detect_parser_name(source_url)),
        )
        supabase.table("jobs").update(patch).eq("id", job_id).execute()
        return False

    record_parser_telemetry(
        supabase, job_id=job_id, source_url=source_url, result=result
    )
    updated = _apply_enrichment_patch(row, result, patch)
    supabase.table("jobs").update(patch).eq("id", job_id).execute()
    return updated


async def reparse_job_row(
    supabase: Any,
    job_id: str,
    row: dict,
    *,
    force: bool = False,
) -> bool:
    """Re-run deep-link parsers (for backfill when first pass missed contacts)."""
    source_url = str(row.get("source_url") or "")
    if not source_url.startswith(("http://", "https://")):
        return False

    try:
        from app.services.deep_link_enricher import enrich_from_source_url

        result = await enrich_from_source_url(source_url)
    except Exception as exc:
        logger.warning("reparse_job_row %s failed: %s", job_id, exc)
        record_parser_telemetry(
            supabase,
            job_id=job_id,
            source_url=source_url,
            result=EnrichmentResult(parser=detect_parser_name(source_url)),
        )
        return False

    record_parser_telemetry(
        supabase, job_id=job_id, source_url=source_url, result=result
    )

    patch: dict[str, Any] = {}
    if force:
        if result.apply_email:
            patch["apply_email"] = result.apply_email
            patch["apply_source"] = "enriched"
        elif result.apply_url:
            patch["apply_url"] = result.apply_url
            patch["apply_source"] = "enriched"
        if result.contact_phone:
            patch["contact_phone"] = result.contact_phone
        if not patch:
            return False
        supabase.table("jobs").update(patch).eq("id", job_id).execute()
        return True

    updated = _apply_enrichment_patch(row, result, patch)
    if patch:
        patch["enrichment_attempted_at"] = datetime.now(timezone.utc).isoformat()
        supabase.table("jobs").update(patch).eq("id", job_id).execute()
    return updated


def schedule_deep_link_enrichment(supabase: Any, job_id: str, row: dict) -> None:
    """Fire-and-forget enrichment after ingest (non-blocking)."""
    if not job_needs_enrichment(row):
        return

    async def _run() -> None:
        try:
            await enrich_job_row(supabase, job_id, row)
        except Exception:
            logger.warning(
                "background deep_link enrichment failed for %s",
                job_id,
                exc_info=True,
            )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        asyncio.run(_run())
