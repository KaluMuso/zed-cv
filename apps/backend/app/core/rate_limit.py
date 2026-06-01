"""Rate limiter instance shared across routes.

Usage in route files:
    from app.core.rate_limit import limiter

    @router.post("/endpoint")
    @limiter.limit("5/minute")
    async def my_endpoint(request: Request, ...):
        ...

Note: The `request: Request` parameter is required by slowapi
even if FastAPI doesn't need it for the route logic.

Storage backend:
- If REDIS_URL is set, slowapi uses Redis as shared storage. Survives
  `docker compose up -d --force-recreate` and works across replicas.
  Use an Upstash REST URL (rediss://default:<token>@<host>:6379) for
  the free serverless option — 10k commands/day covers typical rate-
  limit traffic for this app several times over.
- If REDIS_URL is unset, falls back to in-memory storage. State is
  lost on restart and not shared across replicas — fine for solo dev
  but means a `force-recreate` resets every IP's rate limit. The
  fallback is intentional so a misconfigured prod doesn't crash, but
  health checks should warn when running in production without Redis.
"""
import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def normalize_redis_url(raw: str) -> str:
    """Extract redis:// or rediss:// URL when REDIS_URL was pasted from a CLI snippet."""
    url = raw.strip()
    if not url:
        return ""
    for scheme in ("rediss://", "redis://"):
        idx = url.find(scheme)
        if idx >= 0:
            # Stop at whitespace — e.g. after `redis-cli --tls -u <url>`
            return url[idx:].split()[0]
    return url


def _build_limiter() -> Limiter:
    """Construct the limiter with Redis if REDIS_URL is set, else in-memory.

    Kept as a function so tests can re-import after monkeypatching env. The
    module-level `limiter` below calls this once at import time.
    """
    redis_url = normalize_redis_url(os.environ.get("REDIS_URL", ""))
    if redis_url:
        try:
            return Limiter(
                key_func=get_remote_address,
                default_limits=["200/minute"],
                storage_uri=redis_url,
                # in_memory_fallback_enabled: if Redis goes down mid-request,
                # don't 503 — fall back to local memory for that request.
                # Limits will be soft until Redis returns, which is the
                # right trade for "don't break the app".
                in_memory_fallback_enabled=True,
            )
        except Exception as exc:
            # Misconfigured Redis URL: log and fall through to in-memory
            # so the app still boots. Better than crashing on import.
            logger.error("Rate limiter Redis init failed (%s) — using in-memory fallback", exc)

    return Limiter(key_func=get_remote_address, default_limits=["200/minute"])


limiter = _build_limiter()
