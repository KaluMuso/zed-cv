"""Batch deep-link enrichment for jobs pending secondary scrape (migration 045)."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.services.deep_link_enricher import enrich_job_row
from app.services.description_body_extractor import merge_description_extraction

logger = logging.getLogger(__name__)

_HTTP_SCHEMES = ("http://", "https://")


def _http_source_url(row: dict) -> bool:
    url = (row.get("source_url") or "").strip().lower()
    return url.startswith(_HTTP_SCHEMES)


def _platform_from_url(url: str) -> str | None:
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0] if host else None


def _build_enrichment_patch(row: dict) -> dict[str, Any]:
    """Map apply_* fields to migration-045 contact columns; mark is_enriched."""
    working = dict(row)
    merge_description_extraction(working, working.get("description"))

    apply_url = working.get("apply_url") or row.get("apply_url")
    apply_email = working.get("apply_email") or row.get("apply_email")
    if not apply_url and not apply_email:
        return {}

    patch: dict[str, Any] = {"is_enriched": True}
    source_url = str(row.get("source_url") or "")
    if apply_email:
        patch["contact_email"] = apply_email
    if apply_url:
        if not row.get("original_source_url"):
            patch["original_source_url"] = apply_url
        if not row.get("apply_url"):
            patch["apply_url"] = apply_url
    platform = _platform_from_url(source_url)
    if platform and not row.get("source_platform"):
        patch["source_platform"] = platform[:64]
    return patch


async def run_deep_enrich_tick(supabase: Any, *, limit: int = 25) -> dict[str, int]:
    """Process up to `limit` jobs with is_enriched=false and an HTTP source_url."""
    result = (
        supabase.table("jobs")
        .select(
            "id, source_url, apply_url, apply_email, description, "
            "enrichment_attempted_at, is_enriched, original_source_url, source_platform"
        )
        .eq("is_enriched", False)
        .not_.is_("source_url", "null")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = [r for r in (result.data or []) if _http_source_url(r)]

    processed = 0
    enriched = 0
    unchanged = 0

    for row in rows:
        job_id = str(row["id"])
        processed += 1

        patch = _build_enrichment_patch(row)
        if patch:
            supabase.table("jobs").update(patch).eq("id", job_id).execute()
            enriched += 1
            continue

        try:
            await enrich_job_row(supabase, job_id, row)
        except Exception as exc:
            logger.warning("deep_enrich_tick: enrich_job_row %s failed: %s", job_id, exc)
            unchanged += 1
            continue

        fresh = (
            supabase.table("jobs")
            .select(
                "id, source_url, apply_url, apply_email, description, "
                "original_source_url, source_platform"
            )
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        if not fresh.data:
            unchanged += 1
            continue

        patch = _build_enrichment_patch(fresh.data[0])
        if patch:
            supabase.table("jobs").update(patch).eq("id", job_id).execute()
            enriched += 1
        else:
            unchanged += 1

    return {"processed": processed, "enriched": enriched, "unchanged": unchanged}
