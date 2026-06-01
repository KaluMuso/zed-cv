"""Integration tests for CV parser JSON tolerance (repair + schema fallback)."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.cv_parser import parse_cv_with_llm


@pytest.mark.asyncio
async def test_parse_cv_repairs_markdown_wrapped_json():
    """Near-valid LLM output with fences should parse after repair."""
    wrapped = (
        "```json\n"
        '{"full_name": "Mwape Phiri", "skills": ["python",], '
        '"experience_summary": "Backend engineer", "confidence": 0.88}\n'
        "```"
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=wrapped))]

    with patch("app.services.cv_parser.circuit_is_open", return_value=False), patch(
        "app.services.cv_parser.create_chat_completion_with_retries",
        return_value=mock_response,
    ):
        result = await parse_cv_with_llm("Mwape Phiri\nPython developer at UNZA")

    assert result["full_name"] == "Mwape Phiri"
    assert "python" in result["skills"]
