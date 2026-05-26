"""RFC 7807 problem detail responses and global exception handlers."""
from __future__ import annotations

import logging
import traceback
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"
ERROR_BASE = "https://api.zedapply.com/errors"

_STATUS_TYPE_SUFFIX: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "unprocessable_entity",
    429: "too_many_requests",
    500: "internal_server_error",
    503: "service_unavailable",
}


def get_request_id(request: Request) -> str:
    """Return request id from middleware state, header, or a new UUID."""
    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return str(state_id)
    header = request.headers.get("X-Request-ID")
    if header:
        return header.strip()
    return str(uuid.uuid4())


def _status_title(status: int) -> str:
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    return titles.get(status, "Error")


def _type_suffix(status: int) -> str:
    return _STATUS_TYPE_SUFFIX.get(status, "error")


def _detail_from_exc(exc: HTTPException | StarletteHTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc", ())
                msg = item.get("msg", "")
                parts.append(f"{'.'.join(str(x) for x in loc)}: {msg}")
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else _status_title(exc.status_code)
    return str(detail)


def problem_response(
    request: Request,
    *,
    status: int,
    title: str | None = None,
    detail: str,
    type_suffix: str | None = None,
    user_message: str | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    resolved_title = title or _status_title(status)
    resolved_suffix = type_suffix or _type_suffix(status)
    body: dict[str, Any] = {
        "type": f"{ERROR_BASE}/{resolved_suffix}",
        "title": resolved_title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "request_id": request_id,
    }
    if user_message:
        body["user_message"] = user_message
    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_CONTENT_TYPE,
        headers={"X-Request-ID": request_id},
    )


class ProblemHTTPException(HTTPException):
    """HTTPException that maps to RFC 7807 with a machine `detail` code."""

    def __init__(
        self,
        status_code: int,
        *,
        code: str,
        user_message: str,
        title: str | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=code)
        self.problem_code = code
        self.user_message = user_message
        self.problem_title = title


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    if isinstance(exc, ProblemHTTPException):
        return problem_response(
            request,
            status=exc.status_code,
            title=exc.problem_title,
            detail=exc.problem_code,
            type_suffix=exc.problem_code,
            user_message=exc.user_message,
        )
    return problem_response(
        request,
        status=exc.status_code,
        detail=_detail_from_exc(exc),
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return problem_response(
        request,
        status=exc.status_code,
        detail=_detail_from_exc(exc),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    settings = get_settings()
    request_id = get_request_id(request)
    tb = traceback.format_exc()
    logger.exception(
        "Unhandled exception request_id=%s path=%s",
        request_id,
        request.url.path,
        exc_info=exc,
    )

    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except Exception:
            logger.warning("Sentry capture_exception failed", exc_info=True)

    detail = (
        f"Request id {request_id} failed; engineering has been notified."
    )
    if settings.debug:
        detail = f"{detail}\n{tb}"

    return problem_response(
        request,
        status=500,
        title="Internal Server Error",
        detail=detail,
        type_suffix="internal_server_error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire RFC 7807 handlers for HTTP and unhandled exceptions."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        StarletteHTTPException, starlette_http_exception_handler
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
