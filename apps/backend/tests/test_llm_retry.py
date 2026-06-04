"""Tests for LLM retry/backoff and deferred match-view quota decrement."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError, RateLimitError

from app.lib.retry import (
    call_with_llm_retry,
    circuit_is_open,
    create_chat_completion_with_retries,
    is_retryable_llm_error,
    reset_llm_circuit_for_tests,
)
from app.services import job_deadline_extractor as deadline_mod


@pytest.fixture(autouse=True)
def _reset_circuit():
    reset_llm_circuit_for_tests()
    yield
    reset_llm_circuit_for_tests()


def test_is_retryable_5xx_not_4xx():
    err_500 = APIError("server", request=MagicMock(), body=None)
    err_500.status_code = 500
    assert is_retryable_llm_error(err_500) is True

    err_429 = RateLimitError(
        "rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )
    assert is_retryable_llm_error(err_429) is False


def test_create_chat_completion_retries_twice_then_succeeds():
    client = MagicMock()
    ok = MagicMock(choices=[MagicMock(message=MagicMock(content='{"closing_date": null}'))])
    err = APIError("server", request=MagicMock(), body=None)
    err.status_code = 503
    client.chat.completions.create = MagicMock(side_effect=[err, err, ok])

    with patch("app.lib.retry.time.sleep"):
        out = create_chat_completion_with_retries(
            client,
            log_prefix="test_retry",
            model="test-model",
            messages=[],
        )

    assert out is ok
    assert client.chat.completions.create.call_count == 3
    assert circuit_is_open() is False


@pytest.mark.asyncio
async def test_deadline_extractor_returns_date_after_two_503_retries():
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='{"closing_date": "2026-09-01"}'))
    ]

    client = MagicMock()
    err = APIError("server", request=MagicMock(), body=None)
    err.status_code = 503
    client.chat.completions.create = MagicMock(side_effect=[err, err, mock_resp])

    with patch.object(deadline_mod, "_client", return_value=client):
        with patch.object(deadline_mod.get_settings(), "openrouter_api_key", "test-key"):
            with patch("app.lib.retry.time.sleep"):
                from datetime import date

                result = await deadline_mod.extract_closing_date_llm(
                    "Closing 1 September 2026",
                    title="Analyst",
                    company="ACME",
                )

    assert result == date(2026, 9, 1)
    assert client.chat.completions.create.call_count == 3


def test_circuit_opens_after_ten_consecutive_failures():
    client = MagicMock()
    err = APIError("server", request=MagicMock(), body=None)
    err.status_code = 503
    client.chat.completions.create = MagicMock(side_effect=err)

    with patch("app.lib.retry.time.sleep"):
        for _ in range(10):
            with pytest.raises(APIError):
                create_chat_completion_with_retries(
                    client,
                    log_prefix="circuit_test",
                    model="m",
                    messages=[],
                )

    assert circuit_is_open() is True
    from app.lib.retry import LLMCircuitOpenError

    with pytest.raises(LLMCircuitOpenError):
        call_with_llm_retry(
            lambda: client.chat.completions.create(model="m", messages=[]),
            log_prefix="blocked",
        )

