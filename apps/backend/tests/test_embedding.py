"""Tests for embedding provider routing (Gemini direct vs OpenRouter)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.embedding import generate_embedding


def _gemini_denied_response() -> httpx.Response:
    return httpx.Response(
        403,
        json={
            "error": {
                "code": 403,
                "message": "Your project has been denied access.",
                "status": "PERMISSION_DENIED",
            }
        },
    )


def _vec768(*values: float) -> list[float]:
    base = list(values) if values else [0.1]
    return (base * (768 // len(base) + 1))[:768]


def _gemini_ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"embedding": {"values": _vec768(0.1, 0.2)}, "usageMetadata": {"promptTokenCount": 4}},
    )


def _openrouter_ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [{"embedding": _vec768(0.3, 0.4), "index": 0}],
            "model": "gemini-embedding-001",
            "usage": {"prompt_tokens": 2, "cost": 1.5e-7},
        },
    )


@pytest.mark.asyncio
async def test_embedding_via_openrouter_setting():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_openrouter_ok_response())
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    settings = MagicMock(
        embedding_via_openrouter=True,
        openrouter_api_key="sk-or-test",
        openrouter_base_url="https://openrouter.ai/api/v1",
        embedding_model="gemini-embedding-001",
        embedding_dimensions=768,
    )

    with patch("app.services.embedding.get_settings", return_value=settings), patch(
        "app.services.embedding.circuit_is_open", return_value=False
    ), patch("app.services.embedding.httpx.AsyncClient", return_value=mock_cm), patch(
        "app.services.embedding.record_openrouter_embedding"
    ) as mock_log:
        vec = await generate_embedding("test job")

    assert len(vec) == 768
    assert vec[0] == 0.3
    mock_log.assert_called_once()
    body = mock_client.post.await_args.kwargs.get("json") or mock_client.post.await_args[1].get("json")
    assert body["model"] == "google/gemini-embedding-001"
    assert body["dimensions"] == 768


async def _await_retry(fn, **_kwargs):
    result = fn()
    if hasattr(result, "__await__"):
        return await result
    return result


@pytest.mark.asyncio
async def test_gemini_denied_falls_back_to_openrouter():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[_gemini_denied_response(), _openrouter_ok_response()]
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    settings = MagicMock(
        embedding_via_openrouter=False,
        gemini_api_key="AIza-test",
        openrouter_api_key="sk-or-test",
        openrouter_base_url="https://openrouter.ai/api/v1",
        embedding_model="gemini-embedding-001",
        embedding_dimensions=768,
    )

    with patch("app.services.embedding.get_settings", return_value=settings), patch(
        "app.services.embedding.circuit_is_open", return_value=False
    ), patch("app.services.embedding.async_call_with_llm_retry", side_effect=_await_retry), patch(
        "app.services.embedding.httpx.AsyncClient", return_value=mock_cm
    ), patch("app.services.embedding.record_openrouter_embedding"):
        vec = await generate_embedding("accountant lusaka")

    assert len(vec) == 768
    assert vec[0] == 0.3
    assert mock_client.post.await_count == 2


@pytest.mark.asyncio
async def test_gemini_ok_without_openrouter():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_gemini_ok_response())
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    settings = MagicMock(
        embedding_via_openrouter=False,
        gemini_api_key="AIza-test",
        openrouter_api_key="",
        embedding_model="gemini-embedding-001",
        embedding_dimensions=768,
    )

    with patch("app.services.embedding.get_settings", return_value=settings), patch(
        "app.services.embedding.circuit_is_open", return_value=False
    ), patch("app.services.embedding.async_call_with_llm_retry", side_effect=_await_retry), patch(
        "app.services.embedding.httpx.AsyncClient", return_value=mock_cm
    ), patch("app.services.embedding.record_gemini_embedding") as mock_log:
        vec = await generate_embedding("hello")

    assert len(vec) == 768
    assert vec[0] == 0.1
    mock_log.assert_called_once()
    assert mock_client.post.await_count == 1
