"""Shared OpenRouter chat completion helpers — safe parsing and retries."""
from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from app.lib.retry import (
    LLMCircuitOpenError,
    assert_llm_circuit_closed,
    circuit_is_open,
    create_chat_completion_with_retries,
    is_retryable_llm_error,
)

logger = logging.getLogger(__name__)

# Backwards-compatible exports for tests and callers.
RETRY_BACKOFF_SECONDS = (1, 3, 10)
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
    return is_retryable_llm_error(exc)


__all__ = [
    "LLMCircuitOpenError",
    "MAX_RETRY_ATTEMPTS",
    "RETRY_BACKOFF_SECONDS",
    "assert_llm_circuit_closed",
    "circuit_is_open",
    "create_chat_completion_with_retries",
    "get_completion_content",
    "is_retryable_openrouter_error",
]
