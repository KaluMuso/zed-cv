"""Admin cron endpoints authenticated via admin / ingest API key (n8n)."""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status

from app.core.admin_auth import require_admin_api_key
from app.core.config import Settings, get_settings
from app.core.deps import get_supabase
from app.schemas.admin import DailyDigestBatchResponse, DailyDigestMessage
from app.schemas.matching import BatchMatchAcceptedResponse
from app.services.admin_alerts import check_review_queue_and_alert
from app.services.batch_matching import create_batch_run, run_nightly_batch_match
from app.services.daily_digest import build_daily_digest_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Cron"])


def _require_cron_auth(
    settings: Settings,
    admin_api_key: str | None,
    x_admin_api_key: str | None,
    ingest_api_key: str | None,
    x_ingest_api_key: str | None,
) -> None:
    require_admin_api_key(
        settings,
        admin_api_key=admin_api_key,
        x_admin_api_key=x_admin_api_key,
        ingest_api_key=ingest_api_key,
        x_ingest_api_key=x_ingest_api_key,
    )


@router.post("/check-review-queue")
async def check_review_queue(
    admin_api_key: str | None = Header(None, alias="ADMIN_API_KEY"),
    x_admin_api_key: str | None = Header(None, alias="X-ADMIN-API-KEY"),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Hourly cron: alert admin when review backlog crosses 10/25/50/100 jobs."""
    _require_cron_auth(
        settings, admin_api_key, x_admin_api_key, ingest_api_key, x_ingest_api_key
    )
    return await check_review_queue_and_alert(supabase, settings)


@router.get("/trigger-daily-digest", response_model=DailyDigestBatchResponse)
async def trigger_daily_digest(
    admin_api_key: str | None = Header(None, alias="ADMIN_API_KEY"),
    x_admin_api_key: str | None = Header(None, alias="X-ADMIN-API-KEY"),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """07:00 cron: build WhatsApp digest payloads for verified daily-alert users."""
    _require_cron_auth(
        settings, admin_api_key, x_admin_api_key, ingest_api_key, x_ingest_api_key
    )
    rows = await build_daily_digest_batch(supabase)
    return DailyDigestBatchResponse(
        messages=[DailyDigestMessage(**row) for row in rows],
    )


async def _run_batch_match_task(
    batch_id: str, supabase, settings: Settings
) -> None:
    try:
        await run_nightly_batch_match(supabase, batch_id, settings=settings)
    except Exception:
        logger.exception("nightly batch-match task failed batch_id=%s", batch_id)


@router.post(
    "/batch-match",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchMatchAcceptedResponse,
)
async def batch_match(
    background_tasks: BackgroundTasks,
    admin_api_key: str | None = Header(None, alias="ADMIN_API_KEY"),
    x_admin_api_key: str | None = Header(None, alias="X-ADMIN-API-KEY"),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    supabase=Depends(get_supabase),
    settings: Settings = Depends(get_settings),
):
    """Nightly cron: precompute matches for all active users (n8n 02:00 CAT)."""
    _require_cron_auth(
        settings, admin_api_key, x_admin_api_key, ingest_api_key, x_ingest_api_key
    )
    batch_id = await create_batch_run(supabase)
    background_tasks.add_task(_run_batch_match_task, batch_id, supabase, settings)
    return BatchMatchAcceptedResponse(
        batch_run_id=batch_id,
        message="Batch matching started",
    )
