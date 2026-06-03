"""Gemini direct batch LLM routing and OpenRouter fallback."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deep_enrich import DeepEnrichRole, _call_deep_enrich_llm
from app.services.gemini_direct import QuotaExhaustedError


@pytest.mark.asyncio
async def test_deep_enrich_gemini_quota_exhausted_fallback():
    """429/quota on Gemini direct should call OpenRouter for deep_enrich."""
    mock_settings = MagicMock()
    mock_settings.llm_provider_batch = "gemini_direct"
    mock_settings.gemini_api_key = "gk-test"
    mock_settings.openrouter_api_key = "or-test"
    mock_settings.openrouter_base_url = "https://openrouter.ai/api/v1"
    mock_settings.llm_model = "google/gemini-2.5-flash"

    role = DeepEnrichRole.model_validate(
        {
            "title": "Engineer",
            "description_md": "## Role\n\n" + ("detail " * 8),
            "skills_required": ["a", "b", "c", "d", "e"],
        }
    )

    with patch("app.services.deep_enrich.get_settings", return_value=mock_settings):
        with patch(
            "app.services.deep_enrich.generate_json",
            new_callable=AsyncMock,
            side_effect=QuotaExhaustedError("quota"),
        ):
            with patch(
                "app.services.deep_enrich._call_deep_enrich_llm_openrouter",
                return_value=[role],
            ) as mock_openrouter:
                with patch("app.services.deep_enrich.OpenAI"):
                    roles = await _call_deep_enrich_llm("page text " * 20)

    assert len(roles) == 1
    assert roles[0].title == "Engineer"
    mock_openrouter.assert_called_once()


@pytest.mark.asyncio
async def test_generate_json_quota_raises():
    from app.services import gemini_direct

    mock_settings = MagicMock()
    mock_settings.gemini_api_key = "gk-test"

    with patch("app.services.gemini_direct.get_settings", return_value=mock_settings):
        with patch("app.services.gemini_direct._get_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(
                side_effect=Exception("429 RESOURCE_EXHAUSTED")
            )
            with pytest.raises(QuotaExhaustedError):
                await gemini_direct.generate_json("hi", feature="test")
