"""Admin API for Bwana platform config and escalation smoke tests."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_supabase, require_admin
from app.schemas.bwana_config import (
    BwanaAnalyticsSummary,
    BwanaConfig,
    BwanaConfigPatch,
    BwanaConfigPreview,
)
from app.services.bwana_analytics import fetch_bwana_analytics
from app.services.bwana_config import (
    clear_bwana_config_cache,
    config_row_for_db,
    get_bwana_config,
    preview_system_prompt,
)
from app.services.bwana_chat import send_test_escalation_whatsapp

router = APIRouter(
    prefix="/admin/bwana",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/config", response_model=BwanaConfig)
async def get_admin_bwana_config(
    supabase=Depends(get_supabase),
) -> BwanaConfig:
    return get_bwana_config(supabase, force=True)


@router.patch("/config", response_model=BwanaConfig)
async def patch_admin_bwana_config(
    body: BwanaConfigPatch,
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
) -> BwanaConfig:
    existing = get_bwana_config(supabase, force=True)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return existing

    merged = existing.model_dump()
    merged.update(patch)
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    merged["updated_by"] = current_user["id"]

    try:
        validated = BwanaConfig.model_validate(merged)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = config_row_for_db(validated)
    row.pop("id", None)
    supabase.table("bwana_platform_config").upsert(
        {"id": 1, **row},
        on_conflict="id",
    ).execute()
    clear_bwana_config_cache()
    return validated


@router.get("/config/preview", response_model=BwanaConfigPreview)
async def get_bwana_prompt_preview(
    supabase=Depends(get_supabase),
) -> BwanaConfigPreview:
    prompt, count = await preview_system_prompt(supabase)
    truncated = prompt[:8000] + ("…" if len(prompt) > 8000 else "")
    return BwanaConfigPreview(system_prompt_preview=truncated, char_count=count)


@router.get("/analytics", response_model=BwanaAnalyticsSummary)
async def get_bwana_analytics(
    days: int = 7,
    supabase=Depends(get_supabase),
) -> BwanaAnalyticsSummary:
    if days < 1 or days > 90:
        raise HTTPException(status_code=422, detail="days must be 1–90")
    return fetch_bwana_analytics(supabase, days=days)


@router.post("/test-escalation")
async def test_bwana_escalation(
    supabase=Depends(get_supabase),
) -> dict[str, str]:
    try:
        await send_test_escalation_whatsapp(supabase)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"WhatsApp test failed: {exc}",
        ) from exc
    return {"status": "sent", "detail": "Test message sent to escalation WhatsApp."}
