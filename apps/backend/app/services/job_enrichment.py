"""Apply LLM job enrichment to the database (ingest + backfill)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.job_enricher import JobEnrichment
from app.services.skill_resolver import resolve_skill_ids

logger = logging.getLogger(__name__)


def _emit_analytics_event(
    supabase: Any,
    event: str,
    properties: dict,
    user_id: Optional[str],
) -> None:
    try:
        supabase.table("analytics_events").insert(
            {"event": event, "properties": properties, "user_id": user_id}
        ).execute()
    except Exception as exc:  # pragma: no cover
        logger.debug("analytics_events insert failed (%s): %s", event, exc)


async def apply_job_enrichment(
    supabase: Any,
    *,
    job_id: str,
    job_row: dict,
    enrichment: JobEnrichment,
    source: str = "ingest",
) -> dict[str, Any]:
    """Merge enriched skills and set enums only when currently NULL.

    Returns summary stats used for analytics and backfill reporting.
    """
    existing_links = (
        supabase.table("job_skills")
        .select("skill_id")
        .eq("job_id", job_id)
        .execute()
    )
    existing_ids = {
        row["skill_id"]
        for row in (existing_links.data or [])
        if row.get("skill_id")
    }

    skill_ids = await resolve_skill_ids(
        enrichment.skills,
        supabase=supabase,
        source="scraper_enriched",
        user_id=None,
    )
    new_skill_ids = [sid for sid in skill_ids if sid not in existing_ids]
    for skill_id in new_skill_ids:
        supabase.table("job_skills").insert(
            {"job_id": job_id, "skill_id": skill_id}
        ).execute()

    patch: dict[str, str] = {}
    employment_type_set = False
    work_arrangement_set = False

    if job_row.get("employment_type") is None and enrichment.employment_type:
        patch["employment_type"] = enrichment.employment_type
        employment_type_set = True
    if job_row.get("work_arrangement") is None and enrichment.work_arrangement:
        patch["work_arrangement"] = enrichment.work_arrangement
        work_arrangement_set = True

    if patch:
        supabase.table("jobs").update(patch).eq("id", job_id).execute()

    stats = {
        "job_id": job_id,
        "skills_added": len(new_skill_ids),
        "employment_type_set": employment_type_set,
        "work_arrangement_set": work_arrangement_set,
        "source": source,
    }
    _emit_analytics_event(
        supabase,
        "job_enriched",
        stats,
        user_id=None,
    )
    return stats
