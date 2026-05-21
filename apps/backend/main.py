"""Zed CV API entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter
from app.api.v1 import (
    auth,
    jobs,
    matches,
    cv,
    webhooks,
    profile,
    subscription,
    cover_letter,
    admin,
    interview_prep,
    me,
    contact,
    stats,
    legal,
    preferences,
    users,
    tier_config_routes,
    whatsapp_scraper_webhook,
    analytics,
)

TRUSTED_HOSTS = [
    "api.zedapply.com",
    "*.zedapply.com",
    "localhost",
    "127.0.0.1",
    "zedcv-backend",
]


def create_app() -> FastAPI:
    """Build the FastAPI application (middleware, routes, handlers)."""
    settings = get_settings()
    docs_url = "/docs" if settings.debug else None
    redoc_url = "/redoc" if settings.debug else None
    openapi_url = "/openapi.json" if settings.debug else None

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded, _rate_limit_exceeded_handler
    )
    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "https://www.zedapply.com",
            "https://zedapply.com",
            "https://zed-cv.vercel.app",
            "https://zedcv.vercel.app",
        ],
        allow_origin_regex=(
            r"https://zed-cv-[a-z0-9-]+-vergeo-projects\.vercel\.app"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=TRUSTED_HOSTS,
    )

    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(jobs.router, prefix="/api/v1")
    application.include_router(matches.router, prefix="/api/v1")
    application.include_router(cv.router, prefix="/api/v1")
    application.include_router(profile.router, prefix="/api/v1")
    application.include_router(subscription.router, prefix="/api/v1")
    application.include_router(cover_letter.router, prefix="/api/v1")
    from app.api.v1 import admin_review_jobs

    application.include_router(admin.router, prefix="/api/v1")
    application.include_router(admin_review_jobs.router, prefix="/api/v1")
    application.include_router(interview_prep.router, prefix="/api/v1")
    application.include_router(me.router, prefix="/api/v1")
    application.include_router(contact.router, prefix="/api/v1")
    application.include_router(stats.router, prefix="/api/v1")
    application.include_router(preferences.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(webhooks.router, prefix="/api/v1")
    application.include_router(
        whatsapp_scraper_webhook.router, prefix="/api/v1"
    )
    application.include_router(analytics.router, prefix="/api/v1")
    application.include_router(legal.public_router, prefix="/api/v1")
    application.include_router(legal.admin_router, prefix="/api/v1")
    application.include_router(tier_config_routes.public_router, prefix="/api/v1")
    application.include_router(tier_config_routes.admin_router, prefix="/api/v1")

    @application.on_event("startup")
    async def bootstrap_waha_session() -> None:
        """Ensure WAHA has a WORKING session before users hit /auth/otp/request."""
        import asyncio
        import logging
        from app.services.whatsapp import ensure_session_started

        async def _bootstrap() -> None:
            log = logging.getLogger(__name__)
            try:
                ok = await ensure_session_started("default", timeout_seconds=45)
                if ok:
                    log.info("WAHA session bootstrap: default session is WORKING")
                else:
                    log.warning(
                        "WAHA session bootstrap: default session did not reach "
                        "WORKING within 45s. OTP delivery will fail with 503 "
                        "until session is started manually (POST /api/sessions/start)."
                    )
            except Exception as e:
                log.warning(
                    "WAHA session bootstrap raised non-fatal error: %s", e
                )

        asyncio.create_task(_bootstrap())

        from app.services.whatsapp_scraper import bootstrap_scrape_channels

        asyncio.create_task(bootstrap_scrape_channels())

    @application.get("/api/v1/health")
    async def health_check():
        from app.services.whatsapp import check_waha_health
        from app.core.deps import get_supabase

        waha_ok = await check_waha_health()
        supabase_ok = False
        try:
            supabase_ok = bool(get_supabase().rpc("heartbeat").execute().data)
        except Exception:
            pass
        st = (
            "healthy"
            if (supabase_ok and waha_ok)
            else ("unhealthy" if not supabase_ok else "degraded")
        )
        return {
            "status": st,
            "version": settings.app_version,
            "supabase": supabase_ok,
            "waha": waha_ok,
        }

    if settings.debug:

        @application.get("/api/v1/test-error")
        async def test_error() -> None:
            raise RuntimeError("deliberate test error")

    return application


# ── Observability: Sentry (no-op if SENTRY_DSN is empty) ──
_settings = get_settings()
if _settings.sentry_dsn:
    import sentry_sdk
    from app.core.sentry_redaction import before_send as _sentry_before_send

    sentry_sdk.init(
        dsn=_settings.sentry_dsn,
        environment=_settings.sentry_environment,
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=_sentry_before_send,
    )

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=_settings.debug,
    )
