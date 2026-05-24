"""Interview preparation notes via OpenRouter (google/gemini-flash-2.0).

Mirrors cover_letter and cv_generator services. Single public entry:
  generate_interview_prep(cv_text, job_title, company?, job_description?)
returning {content, sections, word_count}.
"""
import asyncio
import json
import logging
from functools import lru_cache

from openai import OpenAI, AuthenticationError, RateLimitError, APIError

from app.core.config import get_settings
from app.lib.retry import DEGRADED_LLM_USER_MESSAGE, circuit_is_open, degraded_llm_result
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

logger = logging.getLogger(__name__)


INTERVIEW_PREP_SYSTEM_PROMPT = """You are an interview coach for the Zambian job market.

The candidate just got an interview call for a specific role. Produce a focused prep brief
that helps them walk in confident in 15-20 minutes of reading.

Cover these sections, in this order, each as a markdown H2 heading:

  ## Snapshot
  3-4 sentences: what the role is about, why the candidate's background fits, top risk to address.

  ## Likely questions
  6-8 questions the interviewer is most likely to ask, mixing technical/role-specific
  and behavioural. For each question, include a 2-3 sentence "How to answer" hint that
  references the candidate's actual CV — do not invent experience.

  ## Your strengths to emphasise
  4-6 specific bullets pulled from the CV that the candidate should weave into answers.
  Reference numbers/results where the CV has them.

  ## Gaps to acknowledge gracefully
  2-4 places where the role asks for something the CV doesn't show. For each, a one-line
  honest framing (don't fake it; show willingness to learn or transferable experience).

  ## Questions you should ask them
  4-5 thoughtful questions for the candidate to ask the interviewer — show curiosity and
  signal that they understand the role.

  ## Logistics checklist
  Short bullets: what to bring, what to wear (Zambian business norms — business formal
  for banking/government, business casual for tech), how to follow up.

Zambia-specific guidance:
  - Treat UNZA, CBU, Mulungushi, Cavendish, ZCAS, DMI as legitimate institutions.
  - Default to addressing the interviewer formally; first names only if the candidate
    is told otherwise.
  - For salary questions, suggest deferring to second-round unless explicitly asked.

Output rules:
  - Plain markdown text. No JSON wrapper. No code fences around the whole thing.
  - Concise, scannable. No fluff.
"""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


async def generate_interview_prep(
    cv_text: str,
    job_title: str,
    company: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Produce an interview prep brief tailored to the role + candidate."""
    if circuit_is_open():
        return degraded_llm_result(
            content=DEGRADED_LLM_USER_MESSAGE,
            word_count=0,
        )

    settings = get_settings()
    client = _client()

    target = job_title + (f" at {company}" if company else "")
    job_block = (
        f"\n\n--- JOB DESCRIPTION ---\n{job_description[:3000]}"
        if job_description else ""
    )
    user_prompt = (
        f"Create an interview prep brief for: {target}.\n\n"
        f"--- CANDIDATE CV ---\n{cv_text[:6000]}{job_block}"
    )

    def _call():
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="interview_prep",
                model=settings.llm_model,
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": INTERVIEW_PREP_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = get_completion_content(response, default="")
            if content is None:
                logger.warning("interview_prep_skip: bad response: empty choices")
                raise ValueError("Interview prep service is temporarily unavailable. Please try again later.")
            content = content.strip()
            if not content:
                raise ValueError("Empty response from interview prep service")
            return {"content": content, "word_count": len(content.split())}
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for interview prep")
            raise ValueError("Interview prep is not configured. Please contact support.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during interview prep")
            raise ValueError("Interview prep is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error(f"OpenRouter API error during interview prep: {e}")
            raise ValueError("Interview prep is temporarily unavailable. Please try again later.")
        except json.JSONDecodeError:
            raise ValueError("Could not generate prep notes. Please try again.")

    return await asyncio.to_thread(_call)
