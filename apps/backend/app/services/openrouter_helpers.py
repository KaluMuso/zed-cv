"""Shared OpenRouter chat completion helpers — safe parsing and retries."""
from __future__ import annotations

import logging
import time
from typing import Any

from openai import APIError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

RETRY_BACKOFF_SECONDS = (2, 4, 8)
MAX_RETRY_ATTEMPTS = 3


def get_completion_content(
    response: Any,
    *,
    default: str = "{}",
) -> str | None:
    """Extract assistant message content; None when choices/message are missing."""
    try:
        if (
            response
            and response.choices
            and response.choices[0]
            and response.choices[0].message
        ):
            content = response.choices[0].message.content
            return content if content is not None else default
        return None
    except (AttributeError, IndexError, TypeError):
        return None


def is_retryable_openrouter_error(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIError):
        status = getattr(exc, "status_code", None)
        if status is None:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None) if response else None
        return status in (429, 500, 502, 503, 504)
    return False


def create_chat_completion_with_retries(
    client: OpenAI,
    *,
    log_prefix: str = "openrouter",
    **kwargs: Any,
) -> Any:
    """Call chat.completions.create with up to 3 retries on 429 / 5xx."""
    last_error: BaseException | None = None
    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_RETRY_ATTEMPTS or not is_retryable_openrouter_error(exc):
                raise
            delay = RETRY_BACKOFF_SECONDS[attempt]
            logger.warning(
                "%s retry %s/%s in %ss: %s",
                log_prefix,
                attempt + 1,
                MAX_RETRY_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("openrouter chat completion failed without error")
