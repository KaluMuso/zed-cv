"""Security and request-context ASGI middleware."""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.llm import LlmLogContext, reset_llm_context, set_llm_context

SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a per-request id and attach baseline security headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", "").strip()
        if not request_id:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        route = f"{request.method} {request.url.path}"
        ctx_token = set_llm_context(
            LlmLogContext(
                feature="other",
                route=route[:128],
                request_id=request_id,
            )
        )
        try:
            response = await call_next(request)
        finally:
            reset_llm_context(ctx_token)

        response.headers["X-Request-ID"] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response
