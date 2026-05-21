"""Tests for job_deadline_extractor OpenRouter response handling."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.services import job_deadline_extractor as mod
from app.services.openrouter_helpers import create_chat_completion_with_retries


@pytest.mark.asyncio
async def test_deadline_extractor_handles_none_response():
    mock_resp = MagicMock()
    mock_resp.choices = None

    with patch.object(mod, "_client") as mock_client:
        mock_client.return_value = MagicMock()
        with patch.object(mod.get_settings(), "openrouter_api_key", "test-key"):
            with patch.object(
                mod,
                "create_chat_completion_with_retries",
                return_value=mock_resp,
            ):
                result = await mod.extract_closing_date_llm(
                    "Apply by 2026-06-15",
                    title="Role",
                    company="Co",
                    job_id="job-1",
                )

    assert result is None


@pytest.mark.asyncio
async def test_deadline_extractor_retries_on_429():
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='{"closing_date": "2026-09-01"}'))
    ]

    client = MagicMock()
    rate_err = RateLimitError(
        "rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )
    client.chat.completions.create = MagicMock(
        side_effect=[rate_err, rate_err, mock_resp]
    )

    with patch.object(mod, "_client", return_value=client):
        with patch.object(mod.get_settings(), "openrouter_api_key", "test-key"):
            with patch("app.services.openrouter_helpers.time.sleep"):
                result = await mod.extract_closing_date_llm(
                    "Closing 1 September 2026",
                    title="Analyst",
                    company="ACME",
                )

    assert result == date(2026, 9, 1)
    assert client.chat.completions.create.call_count == 3


def test_create_chat_completion_with_retries_on_429():
    client = MagicMock()
    ok = MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])
    err = RateLimitError(
        "rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )
    client.chat.completions.create = MagicMock(side_effect=[err, ok])

    with patch("app.services.openrouter_helpers.time.sleep"):
        out = create_chat_completion_with_retries(
            client,
            log_prefix="test",
            model="test-model",
            messages=[],
        )

    assert out is ok
    assert client.chat.completions.create.call_count == 2
