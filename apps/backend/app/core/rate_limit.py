"""Rate limiter instance shared across routes.

Usage in route files:
    from app.core.rate_limit import limiter
    from app.dependencies.rate_limit import apply_rate_limits, client_ip_key

    @router.post("/endpoint")
    @apply_rate_limits(("5/hour", client_ip_key),))
    async def my_endpoint(request: Request, ...):
        ...

Storage backend:
- If REDIS_URL is set, slowapi uses Redis as shared storage. Survives
  `docker compose up -d --force-recreate` and works across replicas.
- If REDIS_URL is unset, falls back to in-memory storage. State is
  lost on restart and not shared across replicas.
"""
import logging
import os

from slowapi import Limiter

from app.dependencies.rate_limit import client_ip_key

logger = logging.getLogger(__name__)


def _build_limiter() -> Limiter:
    """Construct the limiter with Redis if REDIS_URL is set, else in-memory."""
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            return Limiter(
                key_func=client_ip_key,
                default_limits=["200/minute"],
                storage_uri=redis_url,
                in_memory_fallback_enabled=True,
                # False: FastAPI routes often return plain dicts; slowapi would
                # 500 trying to inject X-RateLimit-* on non-Response objects.
                # Retry-After is added in rate_limit_exceeded_handler instead.
                headers_enabled=False,
            )
        except Exception as exc:
            logger.error(
                "Rate limiter Redis init failed (%s) — using in-memory fallback",
                exc,
            )

    return Limiter(
        key_func=client_ip_key,
        default_limits=["200/minute"],
        headers_enabled=False,
    )


limiter = _build_limiter()
