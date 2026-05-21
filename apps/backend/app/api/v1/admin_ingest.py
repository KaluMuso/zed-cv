"""Admin cron endpoints authenticated via INGEST_API_KEY (n8n)."""
from fastapi import APIRouter, Depends, Header

from app.api.v1.matches import _require_ingest_header
from app.core.config import Settings, get_settings
from app.core.deps import get_supabase
from app.services.admin_alerts import check_review_queue_and_alert

router = APIRouter(prefix="/admin", tags=["Admin Cron"])


@router.post("/check-review-queue")
async def check_review_queue(
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Hourly cron: alert admin when review backlog crosses 10/25/50/100 jobs."""
    _require_ingest_header(settings, ingest_api_key, x_ingest_api_key)
    return await check_review_queue_and_alert(supabase, settings)
