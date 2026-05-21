"""Cover letter generation via OpenRouter (google/gemini-flash-2.0).

Uses the OpenAI-compatible SDK pointed at OpenRouter.
"""
import asyncio
import logging
from typing import Literal
from functools import lru_cache

from openai import OpenAI, AuthenticationError, RateLimitError, APIError

from app.core.config import get_settings
from app.services.openrouter_helpers import get_completion_content

logger = logging.getLogger(__name__)

ToneType = Literal["formal", "friendly", "confident"]

COVER_LETTER_SYSTEM_PROMPT = """You are an expert cover letter writer for the Zambian job market.

Write a professional, compelling cover letter that:
1. Opens with a strong hook connecting the candidate's experience to the role
2. Highlights 2-3 most relevant skills/experiences from their CV that match the job
3. Shows knowledge of the company (if company name provided)
4. Closes with a clear call to action
5. Keeps it to 3-4 paragraphs (250-350 words)

Zambia-specific guidance:
- Use professional but warm language appropriate for Zambian business culture
- Reference local qualifications naturally (UNZA, CBU, ZCAS, etc.)
- If location matches, mention willingness/proximity
- Use "Dear Hiring Manager" if no contact name available
- Sign off with "Yours faithfully" for formal, "Kind regards" for friendly

Tone options:
- formal: Conservative, traditional business language. Suitable for banking, government, NGO roles.
- friendly: Warm and personable while professional. Good for startups, tech, hospitality.
- confident: Bold, achievement-focused, assertive. Best for sales, leadership, competitive roles.

Return ONLY the cover letter text. No JSON, no markdown, no explanation."""


@lru_cache(maxsize=1)
def _get_openrouter_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


async def generate_cover_letter(
    user_cv_text: str,
    job_title: str,
    job_description: str,
    company: str | None = None,
    tone: ToneType = "formal",
) -> dict:
    """Generate a tailored cover letter using Gemini Flash via OpenRouter.

    Returns: {"letter": str, "word_count": int, "tone": str}
    """
    settings = get_settings()
    client = _get_openrouter_client()

    company_line = f" at {company}" if company else ""
    user_prompt = (
        f"Write a {tone} cover letter for this candidate applying to "
        f"'{job_title}'{company_line}.\n\n"
        f"--- CANDIDATE CV ---\n{user_cv_text[:4000]}\n\n"
        f"--- JOB DESCRIPTION ---\n{job_description[:3000]}"
    )

    def _call():
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            letter_text = get_completion_content(response, default="")
            if letter_text is None:
                logger.warning("cover_letter_skip: bad response: empty choices")
                raise ValueError("Cover letter service is temporarily unavailable. Please try again later.")
            letter_text = letter_text.strip()
            word_count = len(letter_text.split())

            return {
                "letter": letter_text,
                "word_count": word_count,
                "tone": tone,
            }

        except AuthenticationError:
            logger.error("OpenRouter API key invalid for cover letter generation")
            raise ValueError("Cover letter service is not configured. Please contact support.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during cover letter generation")
            raise ValueError("Cover letter service is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error(f"OpenRouter API error during cover letter generation: {e}")
            raise ValueError("Cover letter service is temporarily unavailable. Please try again later.")

    return await asyncio.to_thread(_call)
