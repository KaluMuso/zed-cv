"""Tests for image-scanned PDF vision OCR fallback."""
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services.cv_vision_parser import (
    is_vision_parse_empty,
    parse_cv_via_vision,
    vision_parsed_to_raw_text,
)


def _minimal_valid_parse() -> dict:
    return {
        "full_name": "Jane Banda",
        "email": "jane@example.com",
        "phone": "+260971234567",
        "location": "Lusaka",
        "years_experience": 5,
        "skills": ["python", "sql"],
        "experience_summary": "Software engineer with five years of experience.",
        "education": ["BSc Computer Science, UNZA"],
        "confidence": 0.85,
        "sections": None,
    }


@pytest.mark.asyncio
async def test_vision_parser_uses_gemini_multimodal():
    """Vision path sends PNG pages as image_url parts in the user message."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"full_name": "Jane Banda", "skills": ["python"], '
                '"experience_summary": "Engineer with experience", "confidence": 0.9}'
            )
        )
    ]
    mock_response.usage = MagicMock(prompt_tokens=1200, completion_tokens=400)

    fake_page = Image.new("RGB", (100, 100), color=(255, 255, 255))

    with patch("app.services.cv_vision_parser.convert_from_bytes", return_value=[fake_page]), patch(
        "app.services.cv_vision_parser.create_chat_completion_with_retries",
        return_value=mock_response,
    ) as mock_create:
        result = await parse_cv_via_vision(b"%PDF-fake")

    assert result["full_name"] == "Jane Banda"
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "google/gemini-2.5-flash"
    messages = call_kwargs["messages"]
    user_content = messages[1]["content"]
    assert user_content[0]["type"] == "text"
    image_parts = [p for p in user_content if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_vision_parser_disabled_raises():
    with patch("app.services.cv_vision_parser.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(cv_vision_ocr_enabled=False)
        with pytest.raises(ValueError, match="disabled"):
            await parse_cv_via_vision(b"pdf")


def test_is_vision_parse_empty():
    assert is_vision_parse_empty({}) is True
    assert is_vision_parse_empty({"full_name": "", "skills": []}) is True
    assert is_vision_parse_empty(_minimal_valid_parse()) is False


def test_vision_parsed_to_raw_text_includes_skills():
    text = vision_parsed_to_raw_text(_minimal_valid_parse())
    assert "Jane Banda" in text
    assert "python" in text
