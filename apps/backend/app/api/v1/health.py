"""Public health probe — no auth required (UptimeRobot, load balancers)."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.deps import get_supabase
from app.core.rate_limit import normalize_redis_url
from app.services.web_push import vapid_configured
from app.services.whatsapp import check_waha_health

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])

_REDIS_PING_TIMEOUT_SEC = 1.5


async def _check_redis() -> bool | None:
    """Return True/False when REDIS_URL is set; None when unset."""
    redis_url = normalize_redis_url(os.environ.get("REDIS_URL", ""))
    if not redis_url:
        return None

    def _ping() -> bool:
        try:
            import redis

            client = redis.from_url(
                redis_url,
                socket_connect_timeout=_REDIS_PING_TIMEOUT_SEC,
                socket_timeout=_REDIS_PING_TIMEOUT_SEC,
            )
            return bool(client.ping())
        except Exception as exc:
            logger.debug("Redis health ping failed: %s", exc)
            return False

    return await asyncio.to_thread(_ping)


async def _check_supabase() -> bool:
    try:
        return bool(get_supabase().rpc("heartbeat").execute().data)
    except Exception:
        return False


def _derive_status(*, supabase_ok: bool, waha_ok: bool) -> str:
    if supabase_ok and waha_ok:
        return "healthy"
    if supabase_ok:
        return "degraded"
    return "unhealthy"


async def build_health_payload(settings: Settings) -> dict[str, Any]:
    """Assemble /health JSON — shared by route and tests."""
    waha_ok, supabase_ok, redis_ok = await asyncio.gather(
        check_waha_health(),
        _check_supabase(),
        _check_redis(),
    )
    status = _derive_status(supabase_ok=supabase_ok, waha_ok=waha_ok)

    payload: dict[str, Any] = {
        "status": status,
        "version": settings.app_version,
        "supabase": supabase_ok,
        "waha": waha_ok,
        "redis_configured": redis_ok is not None,
        "vapid_configured": vapid_configured(settings),
        "resend_configured": bool(settings.resend_api_key.strip()),
        "sentry_configured": bool(settings.sentry_dsn.strip()),
    }
    if redis_ok is not None:
        payload["redis"] = redis_ok
    return payload


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return await build_health_payload(settings)
