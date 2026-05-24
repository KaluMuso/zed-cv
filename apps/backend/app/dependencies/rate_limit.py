"""Reusable SlowAPI key functions, middleware, and RFC 7807 429 handler.

Trust X-Forwarded-For (first hop) because Caddy terminates TLS in front of
uvicorn. Authenticated routes should key by user id when a Bearer JWT is
present; otherwise fall back to client IP.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.errors import problem_response

logger = logging.getLogger(__name__)

# Paths where the JSON body includes `phone` for per-phone rate buckets.
_OTP_PHONE_PATHS = frozenset({
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
})


def client_ip_key(request: Request) -> str:
    """Client IP behind Caddy: first X-Forwarded-For hop, else direct peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return get_remote_address(request)


def per_user_key(request: Request) -> str:
    """Authenticated user bucket; falls back to IP if JWT missing/invalid."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass
    return f"ip:{client_ip_key(request)}"


def otp_phone_key(request: Request) -> str:
    """Per-phone bucket for OTP routes (set by RateLimitBodyMiddleware)."""
    phone = getattr(request.state, "rate_limit_phone", None)
    if phone:
        return f"phone:{phone}"
    return f"ip:{client_ip_key(request)}"


def apply_rate_limits(
    *specs: tuple[str, Callable[[Request], str]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Stack multiple @limiter.limit decorators (all must pass)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        wrapped = func
        for limit_value, key_func in reversed(specs):
            from app.core.rate_limit import limiter

            wrapped = limiter.limit(limit_value, key_func=key_func)(wrapped)
        return wrapped

    return decorator


class RateLimitBodyMiddleware(BaseHTTPMiddleware):
    """Parse OTP JSON bodies so per-phone SlowAPI keys work before route handlers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            request.method == "POST"
            and request.url.path in _OTP_PHONE_PATHS
        ):
            try:
                raw = await request.body()
                if raw:
                    data = json.loads(raw)
                    phone = data.get("phone")
                    if isinstance(phone, str) and phone.strip():
                        request.state.rate_limit_phone = phone.strip()
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return await call_next(request)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """RFC 7807 problem+json for 429 with Retry-After from SlowAPI window stats."""
    problem = problem_response(
        request,
        status=429,
        title="Too Many Requests",
        detail=f"Rate limit exceeded: {exc.detail}",
        type_suffix="too_many_requests",
    )
    view_limit = getattr(request.state, "view_rate_limit", None)
    app_limiter = getattr(request.app.state, "limiter", None)
    if app_limiter is not None and view_limit is not None:
        try:
            window_stats = app_limiter.limiter.get_window_stats(
                view_limit[0], *view_limit[1]
            )
            reset_in = 1 + window_stats[0]
            problem.headers["Retry-After"] = str(int(reset_in - time.time()))
            problem.headers["X-RateLimit-Limit"] = str(view_limit[0].amount)
            problem.headers["X-RateLimit-Remaining"] = str(window_stats[1])
            problem.headers["X-RateLimit-Reset"] = str(reset_in)
        except Exception:
            logger.warning(
                "Failed to compute rate-limit Retry-After headers",
                exc_info=True,
            )
    return problem


def register_rate_limit_middleware(app: ASGIApp) -> None:
    """Attach OTP body middleware (idempotent if called once from create_app)."""
    app.add_middleware(RateLimitBodyMiddleware)
