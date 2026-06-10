"""Public tier catalog + superadmin tier_config editor."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import (
    get_supabase,
    require_admin_api_key_or_superadmin,
    require_superadmin,
    security_optional,
)
from app.core.config import get_settings, Settings
from app.schemas.tier_config import (
    TierConfigBulkUpdate,
    TierConfigList,
    TierConfigPatch,
    TierConfigRow,
    VALID_TIERS,
)
from app.core.tier_gating import load_user_welcome_fields
from app.services.pricing import (
    effective_checkout_price_ngwee,
    load_user_promotion_until,
    promotion_active,
)
from app.services.tier_config import (
    clear_tier_config_cache,
    fetch_tier_config_rows,
)
from jose import jwt, JWTError

public_router = APIRouter(prefix="/tiers", tags=["Pricing"])

admin_router = APIRouter(
    prefix="/admin/tier-config",
    tags=["Admin"],
    dependencies=[Depends(require_superadmin)],
)

admin_tiers_router = APIRouter(
    prefix="/admin/tiers",
    tags=["Admin"],
    dependencies=[Depends(require_admin_api_key_or_superadmin)],
)

_TIER_SORT_ORDER = {"free": 0, "starter": 1, "professional": 2, "super_standard": 3}

# Monthly billing cycle in days. Annual rows live in tier_config with
# billing_period_days=365; we never apply the first-month welcome promo to
# annual rows because the annual sticker already carries the
# long-commitment discount (e.g. starter monthly K125×12=K1500 → annual
# K1050 = ~30% off). Stacking the welcome 50% on top would charge a
# monthly-half-off amount against an annual commitment and confuse the
# checkout flow.
_MONTHLY_PERIOD_DAYS = 30


async def _optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    settings: Settings = Depends(get_settings),
) -> str | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload.get("sub")
    except JWTError:
        return None


def _rows_to_response(
    rows: list[dict],
    *,
    promotion_until: datetime | None = None,
) -> TierConfigList:
    promo_active = promotion_active(promotion_until) if promotion_until else False
    tiers: list[TierConfigRow] = []
    for r in rows:
        list_price = int(r["price_ngwee"])
        # Migration 111 added billing_period_days to tier_config. Read it
        # through to the response so the frontend can distinguish monthly
        # vs annual rows. Default to 30 for rows that pre-date the
        # migration (e.g. when running against the schema fallback in
        # tier_config.py::_default_rows).
        period_days = int(r.get("billing_period_days") or _MONTHLY_PERIOD_DAYS)
        # Welcome 50% promo applies to monthly tiers only. Annual sticker
        # already discounts; don't stack.
        is_monthly = period_days == _MONTHLY_PERIOD_DAYS
        promo_eligible = promo_active and list_price > 0 and is_monthly
        checkout = (
            effective_checkout_price_ngwee(list_price, promotion_until)
            if promo_eligible
            else None
        )
        row_promo_active = (
            promo_active if (list_price > 0 and is_monthly) else None
        )
        tiers.append(
            TierConfigRow(
                tier=r["tier"],
                display_name=r["display_name"],
                price_ngwee=list_price,
                matches_limit=int(r["matches_limit"]),
                sort_order=int(r.get("sort_order") or 0),
                billing_period_days=period_days,
                updated_at=r.get("updated_at"),
                checkout_price_ngwee=checkout,
                promotion_active=row_promo_active,
            )
        )
    return TierConfigList(tiers=tiers)


def _with_user_promo_fields(
    response: TierConfigList,
    *,
    welcome_row: dict | None,
    promo_until: datetime | None,
) -> TierConfigList:
    if welcome_row is None:
        return response
    welcome_until = welcome_row.get("welcome_match_bonus_until")
    return response.model_copy(
        update={
            "welcome_match_bonus": welcome_row.get("welcome_match_bonus"),
            "welcome_match_bonus_until": welcome_until,
            "promo_until": promo_until,
        }
    )


@public_router.get("", response_model=TierConfigList)
async def list_public_tiers(
    supabase=Depends(get_supabase),
    user_id: str | None = Depends(_optional_user_id),
):
    """Public pricing catalog; authenticated callers get checkout_price_ngwee."""
    rows = await fetch_tier_config_rows(supabase)
    promo_until = None
    welcome_row = None
    if user_id:
        promo_until = await load_user_promotion_until(supabase, user_id)
        welcome_row = await load_user_welcome_fields(user_id, supabase)
    response = _rows_to_response(rows, promotion_until=promo_until)
    return _with_user_promo_fields(
        response, welcome_row=welcome_row, promo_until=promo_until
    )


@admin_tiers_router.get("", response_model=TierConfigList)
async def list_admin_tiers(supabase=Depends(get_supabase)):
    """Admin: list tier pricing and match quotas (API key or superadmin JWT)."""
    rows = await fetch_tier_config_rows(supabase, force=True)
    return _rows_to_response(rows)


@admin_tiers_router.patch("/{tier_name}", response_model=TierConfigRow)
async def patch_admin_tier(
    tier_name: str,
    body: TierConfigPatch,
    auth: dict = Depends(require_admin_api_key_or_superadmin),
    supabase=Depends(get_supabase),
):
    """Admin: update price and match quota for one tier."""
    if tier_name not in VALID_TIERS:
        raise HTTPException(status_code=404, detail=f"Unknown tier: {tier_name}")
    if tier_name == "free" and body.price_ngwee != 0:
        raise HTTPException(
            status_code=422,
            detail="Free tier price must be K0 (price_ngwee=0).",
        )

    existing = (
        supabase.table("tier_config")
        .select("tier, display_name")
        .eq("tier", tier_name)
        .eq("billing_period_days", _MONTHLY_PERIOD_DAYS)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail=f"Tier not configured: {tier_name}")

    now = datetime.now(timezone.utc).isoformat()
    user_id = auth.get("id")
    row = {
        "tier": tier_name,
        "display_name": existing.data[0]["display_name"],
        "price_ngwee": body.price_ngwee,
        "matches_limit": body.matches_limit,
        "sort_order": _TIER_SORT_ORDER[tier_name],
        "billing_period_days": _MONTHLY_PERIOD_DAYS,
        "updated_at": now,
        "updated_by": user_id,
    }
    # PK is composite (tier, billing_period_days) post-migration-111.
    supabase.table("tier_config").upsert(
        row, on_conflict="tier,billing_period_days"
    ).execute()
    clear_tier_config_cache()
    rows = await fetch_tier_config_rows(supabase, force=True)
    updated = next(
        (
            r
            for r in rows
            if r["tier"] == tier_name
            and int(r.get("billing_period_days") or _MONTHLY_PERIOD_DAYS)
            == _MONTHLY_PERIOD_DAYS
        ),
        None,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Tier update failed")
    return _rows_to_response([updated]).tiers[0]


@admin_router.get("", response_model=TierConfigList)
async def get_admin_tier_config(supabase=Depends(get_supabase)):
    """Superadmin: read current tier pricing and match quotas."""
    rows = await fetch_tier_config_rows(supabase, force=True)
    return _rows_to_response(rows)


@admin_router.put("", response_model=TierConfigList)
async def update_admin_tier_config(
    body: TierConfigBulkUpdate,
    current_user: dict = Depends(require_superadmin),
    supabase=Depends(get_supabase),
):
    """Superadmin: replace tier pricing and match quotas."""
    seen: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()
    user_id = current_user["id"]

    for item in body.tiers:
        if item.tier not in VALID_TIERS:
            raise HTTPException(status_code=422, detail=f"Invalid tier: {item.tier}")
        if item.tier in seen:
            raise HTTPException(status_code=422, detail=f"Duplicate tier: {item.tier}")
        seen.add(item.tier)
        if item.tier == "free" and item.price_ngwee != 0:
            raise HTTPException(
                status_code=422,
                detail="Free tier price must be K0 (price_ngwee=0).",
            )

    if seen != VALID_TIERS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Request must include all four tiers: "
                "free, starter, professional, super_standard."
            ),
        )

    for item in sorted(body.tiers, key=lambda t: _TIER_SORT_ORDER[t.tier]):
        # Bulk PUT edits only the monthly tier rows; annual rows are
        # editable separately via a future endpoint. on_conflict matches
        # the composite PK introduced in migration 111.
        supabase.table("tier_config").upsert(
            {
                "tier": item.tier,
                "display_name": item.display_name.strip(),
                "price_ngwee": item.price_ngwee,
                "matches_limit": item.matches_limit,
                "sort_order": _TIER_SORT_ORDER[item.tier],
                "billing_period_days": _MONTHLY_PERIOD_DAYS,
                "updated_at": now,
                "updated_by": user_id,
            },
            on_conflict="tier,billing_period_days",
        ).execute()

    clear_tier_config_cache()
    rows = await fetch_tier_config_rows(supabase, force=True)
    return _rows_to_response(rows)
