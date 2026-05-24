"""OpenAI-backed AI helpers (direct api.openai.com).

Used by job-scoped cover letter generation. Embeddings and most other
LLM calls still go through OpenRouter/Gemini in sibling services.
"""
import asyncio
import logging
from functools import lru_cache

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from app.core.config import get_settings
from app.services.llm import FEATURE_OTHER, LlmLogContext, record_openai_completion

logger = logging.getLogger(__name__)

COVER_LETTER_MODEL = "gpt-4o-mini"

COVER_LETTER_SYSTEM_PROMPT = """You are an expert cover letter writer for the Zambian job market.

Write ONE professional cover letter that:
- Is strictly between 200 and 250 words (never exceed 250 words)
- Maps the candidate's specific skills and experience to the job requirements
- Uses 3 short paragraphs: opening hook, relevant evidence, closing call to action
- Contains no fluff, clichés, or generic filler
- Uses "Dear Hiring Manager" when no contact name is known
- Signs off with "Yours faithfully"

Return ONLY the cover letter body text. No JSON, markdown, titles, or commentary."""


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


async def generate_tailored_cover_letter(
    user_cv_text: str,
    job_description: str,
    company_name: str | None,
    role: str,
) -> dict:
    """Generate a concise cover letter via OpenAI.

    Returns: {"content": str, "word_count": int}
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError(
            "Cover letter service is not configured. Please contact support."
        )

    company_line = f" at {company_name}" if company_name else ""
    user_prompt = (
        f"Write a tailored cover letter for the role '{role}'{company_line}.\n\n"
        f"--- CANDIDATE CV ---\n{user_cv_text[:4000]}\n\n"
        f"--- JOB DESCRIPTION ---\n{job_description[:3000]}"
    )

    def _call() -> dict:
        client = _get_openai_client()
        try:
            response = client.chat.completions.create(
                model=COVER_LETTER_MODEL,
                max_tokens=600,
                temperature=0.4,
                messages=[
                    {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            record_openai_completion(
                response,
                model=COVER_LETTER_MODEL,
                context=LlmLogContext(
                    feature=FEATURE_OTHER,
                    route="POST /api/v1/cover-letter/generate",
                ),
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                logger.warning("ai_service: empty cover letter from OpenAI")
                raise ValueError(
                    "Cover letter service is temporarily unavailable. "
                    "Please try again later."
                )
            word_count = len(content.split())
            return {"content": content, "word_count": word_count}
        except AuthenticationError:
            logger.error("OpenAI API key invalid for cover letter generation")
            raise ValueError(
                "Cover letter service is not configured. Please contact support."
            ) from None
        except RateLimitError:
            logger.warning("OpenAI rate limit during cover letter generation")
            raise ValueError(
                "Cover letter service is temporarily busy. "
                "Please try again in a minute."
            ) from None
        except APIError as exc:
            logger.error("OpenAI API error during cover letter generation: %s", exc)
            raise ValueError(
                "Cover letter service is temporarily unavailable. "
                "Please try again later."
            ) from None

    return await asyncio.to_thread(_call)
