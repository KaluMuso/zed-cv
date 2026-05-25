"""LLM retry with exponential backoff and a consecutive-failure circuit breaker."""
from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from supabase import Client
from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Three attempts total; sleeps between attempts are 1s then 3s (before 2nd and 3rd try).
RETRY_WAIT_SECONDS = (1, 3, 10)
MAX_ATTEMPTS = 3

CIRCUIT_FAILURE_THRESHOLD = 10
CIRCUIT_WINDOW_SECONDS = 300


class LLMCircuitOpenError(Exception):
    """Raised when too many consecutive LLM calls failed within the window."""


DEGRADED_LLM_USER_MESSAGE = (
    "AI features are temporarily degraded. Please try again in a few minutes."
)


def degraded_llm_result(**fields: Any) -> dict[str, Any]:
    """Standard payload when the circuit breaker skips provider calls."""
    return {"degraded": True, **fields}


@dataclass
class _CircuitBreaker:
    """Tracks consecutive failures; opens after 10 in a rolling 5-minute window."""

    failure_times: deque[float] = field(default_factory=deque)
    consecutive_failures: int = 0

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.failure_times.clear()

    def record_failure(self) -> None:
        now = time.monotonic()
        self.consecutive_failures += 1
        self.failure_times.append(now)
        cutoff = now - CIRCUIT_WINDOW_SECONDS
        while self.failure_times and self.failure_times[0] < cutoff:
            self.failure_times.popleft()

    def is_open(self) -> bool:
        now = time.monotonic()
        if self.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
            if self.failure_times:
                last = self.failure_times[-1]
                if now - last > CIRCUIT_WINDOW_SECONDS:
                    self.record_success()
                    return False
            return True
        cutoff = now - CIRCUIT_WINDOW_SECONDS
        while self.failure_times and self.failure_times[0] < cutoff:
            self.failure_times.popleft()
        if not self.failure_times:
            self.consecutive_failures = 0
        return False


_circuit = _CircuitBreaker()


def reset_llm_circuit_for_tests() -> None:
    """Clear circuit state (unit tests only)."""
    _circuit.consecutive_failures = 0
    _circuit.failure_times.clear()


def circuit_is_open() -> bool:
    return _circuit.is_open()


def assert_llm_circuit_closed() -> None:
    if _circuit.is_open():
        raise LLMCircuitOpenError(
            "LLM circuit open: too many consecutive failures; skipping provider calls"
        )


def is_retryable_llm_error(exc: BaseException) -> bool:
    """Retry only 5xx provider errors and network/timeout failures — not 4xx."""
    if isinstance(
        exc,
        (
            APIConnectionError,
            APITimeoutError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            ConnectionError,
            TimeoutError,
        ),
    ):
        return True
    if isinstance(exc, APIError):
        status = _http_status_from_api_error(exc)
        return status is not None and status >= 500
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def _http_status_from_api_error(exc: APIError) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return int(status)
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if code is not None:
            return int(code)
    return None


def _wait_before_attempt(retry_state: Any) -> float:
    """Tenacity wait: 1s before attempt 2, 3s before attempt 3."""
    attempt = retry_state.attempt_number
    if attempt <= 1:
        return 0.0
    idx = min(attempt - 2, len(RETRY_WAIT_SECONDS) - 1)
    return float(RETRY_WAIT_SECONDS[idx])


def _retrying_kwargs() -> dict[str, Any]:
    return {
        "stop": stop_after_attempt(MAX_ATTEMPTS),
        "wait": _wait_before_attempt,
        "retry": retry_if_exception(is_retryable_llm_error),
        "reraise": True,
    }


def call_with_llm_retry(
    fn: Callable[[], T],
    *,
    log_prefix: str = "llm",
) -> T:
    """Run a sync LLM call with retries; updates the circuit breaker."""
    assert_llm_circuit_closed()
    try:
        result: T | None = None
        for attempt in Retrying(**_retrying_kwargs(), sleep=time.sleep):
            with attempt:
                result = fn()
    except Exception as exc:
        _circuit.record_failure()
        logger.error("%s failed after retries: %s", log_prefix, exc)
        raise
    _circuit.record_success()
    assert result is not None
    return result


async def async_call_with_llm_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    log_prefix: str = "llm",
) -> T:
    """Run an async LLM call with retries; updates the circuit breaker."""
    assert_llm_circuit_closed()
    try:
        result: T | None = None
        async for attempt in AsyncRetrying(**_retrying_kwargs()):
            with attempt:
                result = await fn()
    except Exception as exc:
        _circuit.record_failure()
        logger.error("%s failed after retries: %s", log_prefix, exc)
        raise
    _circuit.record_success()
    assert result is not None
    return result


def create_chat_completion_with_retries(
    client: OpenAI,
    *,
    log_prefix: str = "openrouter",
    log_context: Any = None,
    supabase: Client | None = None,
    **kwargs: Any,
) -> Any:
    """OpenRouter/OpenAI chat.completions.create with retry + circuit breaker."""
    from app.services.llm import get_llm_context, record_openrouter_completion

    model = str(kwargs.get("model") or "")
    response = call_with_llm_retry(
        lambda: client.chat.completions.create(**kwargs),
        log_prefix=log_prefix,
    )
    ctx = log_context or get_llm_context()
    if model and ctx is not None:
        record_openrouter_completion(
            response,
            model=model,
            context=ctx,
            supabase=supabase,
        )
    return response


async def gemini_post_with_retries(
    client: httpx.AsyncClient,
    *,
    url: str,
    params: dict[str, str],
    json_body: dict[str, Any],
    log_prefix: str = "gemini",
) -> httpx.Response:
    """POST to Gemini embedContent with retry + circuit breaker."""

    async def _post() -> httpx.Response:
        return await client.post(url, params=params, json=json_body)

    return await async_call_with_llm_retry(_post, log_prefix=log_prefix)
