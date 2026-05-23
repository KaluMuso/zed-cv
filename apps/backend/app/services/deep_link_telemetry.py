"""Telemetry for deep-link parser attempts (ai_cache deep_link_parser rows)."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.schemas.db_enums import CacheType, validate_cache_type
from app.services.deep_link_parsers import EnrichmentResult
from app.services.deep_link_router import detect_parser_name, parser_outcome

logger = logging.getLogger(__name__)


def record_parser_telemetry(
    supabase: Any | None,
    *,
    job_id: str | None,
    source_url: str,
    result: EnrichmentResult,
) -> None:
    """Persist per-parser attempt metrics to ai_cache for admin scraper-stats."""
    if supabase is None:
        return
    parser_name = result.parser or detect_parser_name(source_url)
    outcome = parser_outcome(result)
    cache_key = hashlib.sha256(
        f"deep_link_parser:{job_id or 'none'}:{source_url}:{parser_name}".encode()
    ).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=90)
    row: dict[str, Any] = {
        "cache_key": cache_key,
        "cache_type": validate_cache_type(CacheType.deep_link_parser.value),
        "input_hash": cache_key[:16],
        "result": {"outcome": outcome},
        "model": parser_name,
        "expires_at": expires.isoformat(),
        "metadata": {
            "parser": parser_name,
            "outcome": outcome,
            "job_id": job_id,
            "source_url": source_url[:500],
            "found_email": bool(result.apply_email),
            "found_phone": bool(result.contact_phone),
        },
    }
    try:
        supabase.table("ai_cache").insert(row).execute()
    except Exception:
        logger.debug("parser telemetry insert failed", exc_info=True)
