"""Zed CV API entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.api.v1 import auth, jobs, matches, cv, webhooks, profile, subscription, cover_letter

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version, docs_url="/docs", redoc_url="/redoc")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://zedcv.vercel.app",
        "https://zed-cv.vercel.app",
        "https://www.zedcv.com",
        "https://zedcv.com",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(cv.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(subscription.router, prefix="/api/v1")
app.include_router(cover_letter.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    from app.services.whatsapp import check_waha_health
    from app.core.deps import get_supabase
    waha_ok = await check_waha_health()
    supabase_ok = False
    try:
        supabase_ok = bool(get_supabase().rpc("heartbeat").execute().data)
    except Exception:
        pass
    st = "healthy" if (supabase_ok and waha_ok) else ("unhealthy" if not supabase_ok else "degraded")
    return {"status": st, "version": settings.app_version, "supabase": supabase_ok, "waha": waha_ok}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
