"""CV parsing service — extracts text, skills, and experience from uploaded files."""

import io
import json
from typing import Any

import anthropic
from PyPDF2 import PdfReader
from docx import Document

from app.core.config import get_settings


async def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    """Extract raw text from PDF, DOCX, or image files."""
    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif file_type == "docx":
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs)

    elif file_type in ("jpg", "png", "jpeg"):
        # Use Claude Vision for OCR on image-based CVs
        return await _ocr_with_claude(file_bytes, file_type)

    raise ValueError(f"Unsupported file type: {file_type}")


async def parse_cv_with_llm(raw_text: str) -> dict[str, Any]:
    """Use Claude Haiku to extract structured data from CV text.

    Returns: {
        "full_name": str,
        "email": str | None,
        "phone": str | None,
        "location": str | None,
        "years_experience": int,
        "skills": list[str],
        "experience_summary": str,
        "education": list[str],
        "confidence": float  # 0-1
    }
    """
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Extract structured information from this CV/resume text.
Return ONLY valid JSON with these fields:
- full_name (string)
- email (string or null)
- phone (string or null, format as +260XXXXXXXXX if Zambian)
- location (string or null, city/province in Zambia if applicable)
- years_experience (integer, estimate from work history dates)
- skills (array of strings, lowercase, normalized — e.g. "javascript" not "JS")
- experience_summary (string, 1-2 sentences)
- education (array of strings, highest qualification first)
- confidence (float 0-1, how confident you are in the extraction)

CV TEXT:
{raw_text[:8000]}""",
            }
        ],
    )

    # Parse the JSON response
    text = response.content[0].text
    # Handle markdown code blocks if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


async def _ocr_with_claude(image_bytes: bytes, file_type: str) -> str:
    """Use Claude Vision to extract text from image-based CVs/job flyers."""
    import base64

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    media_type = f"image/{'jpeg' if file_type in ('jpg', 'jpeg') else 'png'}"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract ALL text from this image. This is a CV/resume or job posting. Preserve the structure as much as possible. Return only the extracted text, nothing else.",
                    },
                ],
            }
        ],
    )

    return response.content[0].text
