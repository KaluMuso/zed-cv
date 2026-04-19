"""Zed CV API — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import auth, jobs, matches, cv, webhooks

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Next.js dev
        "https://zedcv.vercel.app",    # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(cv.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint — also used by n8n heartbeat."""
    from app.services.whatsapp import check_waha_health
    from app.core.deps import get_supabase

    waha_ok = await check_waha_health()

    # Quick Supabase check
    supabase_ok = False
    try:
        sb = get_supabase()
        result = sb.rpc("heartbeat").execute()
        supabase_ok = bool(result.data)
    except Exception:
        pass

    status = "healthy" if (supabase_ok and waha_ok) else "degraded"
    if not supabase_ok:
        status = "unhealthy"

    return {
        "status": status,
        "version": settings.app_version,
        "supabase": supabase_ok,
        "waha": waha_ok,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
