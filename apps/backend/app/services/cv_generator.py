"""CV analysis and tailored-CV generation via OpenRouter (google/gemini-flash-2.0).

Mirrors the cover_letter service: same client, same error mapping, same
model. Two public functions:

  - analyze_cv(cv_text) -> {overall, skills, format, impact, strengths[], improvements[]}
  - generate_cv(cv_text, job_title, company?, job_description?) -> {content, word_count}
"""
import asyncio
import json
import logging
from functools import lru_cache

from openai import OpenAI, AuthenticationError, RateLimitError, APIError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


CV_ANALYSIS_SYSTEM_PROMPT = """You are an expert CV reviewer for the Zambian job market.

Score the CV on four dimensions, each 0-100:
  - overall: weighted holistic quality
  - skills: relevance, breadth, and how clearly skills are demonstrated
  - format: structure, readability, length, ATS-friendliness
  - impact: quantified achievements, action verbs, results vs responsibilities

Then list:
  - strengths: 3-5 short bullets the candidate is doing well
  - improvements: 3-5 short bullets they should fix, ranked by impact

Zambia-specific context:
  - Recognize UNZA, CBU, Mulungushi, Cavendish, ZCAS, DMI as legitimate institutions
  - Do not penalise candidates for using "Grade 12" instead of "High School"
  - Prefer concrete numbers ("grew sales 22%") over vague claims

Return ONLY valid JSON in this exact shape:
{
  "overall": <int 0-100>,
  "skills": <int 0-100>,
  "format": <int 0-100>,
  "impact": <int 0-100>,
  "strengths": ["...", "..."],
  "improvements": ["...", "..."]
}"""


CV_GENERATE_SYSTEM_PROMPT = """You are an expert CV writer for the Zambian job market.

Rewrite the candidate's CV tailored to the target role. Keep it truthful — do not invent experience or qualifications. Restructure, sharpen wording, and surface the most relevant accomplishments.

Output rules:
  - Plain text only. No markdown. No JSON.
  - Use clear section headings: SUMMARY, SKILLS, EXPERIENCE, EDUCATION, CERTIFICATIONS (omit empty sections).
  - Lead each experience bullet with an action verb and, where present in the source, a quantified result.
  - Keep it to one page of content (~400-600 words).
  - Use Zambian conventions: phone +260, ZMW currency, local institutions named accurately.
  - Sign-off line not needed (this is a CV, not a cover letter).
"""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _strip_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0]
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0]
    return text


def _clamp(n, lo=0, hi=100) -> int:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return 0
    return max(lo, min(hi, v))


async def analyze_cv(cv_text: str) -> dict:
    """Score a CV and surface strengths/improvements via Gemini Flash."""
    settings = get_settings()
    client = _client()

    def _call():
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": CV_ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Analyse this CV:\n\n{cv_text[:8000]}",
                    },
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(_strip_fences(raw).strip())
            return {
                "overall": _clamp(data.get("overall", 0)),
                "skills": _clamp(data.get("skills", 0)),
                "format": _clamp(data.get("format", 0)),
                "impact": _clamp(data.get("impact", 0)),
                "strengths": [str(s) for s in (data.get("strengths") or [])][:6],
                "improvements": [str(s) for s in (data.get("improvements") or [])][:6],
            }
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for CV analysis")
            raise ValueError("CV analysis is not configured. Please contact support.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during CV analysis")
            raise ValueError("CV analysis is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error(f"OpenRouter API error during CV analysis: {e}")
            raise ValueError("CV analysis is temporarily unavailable. Please try again later.")
        except (json.JSONDecodeError, ValueError):
            logger.error("Failed to parse CV analysis response as JSON")
            raise ValueError("Could not score your CV. Please try again.")

    return await asyncio.to_thread(_call)


async def generate_cv(
    cv_text: str,
    job_title: str,
    company: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Produce a tailored CV draft for the target role."""
    settings = get_settings()
    client = _client()

    target = f"{job_title}" + (f" at {company}" if company else "")
    job_block = f"\n\n--- TARGET JOB DESCRIPTION ---\n{job_description[:3000]}" if job_description else ""
    user_prompt = (
        f"Tailor this CV for: {target}.\n\n"
        f"--- CANDIDATE CV ---\n{cv_text[:6000]}{job_block}"
    )

    def _call():
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": CV_GENERATE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise ValueError("Empty response from CV generator")
            return {"content": content, "word_count": len(content.split())}
        except AuthenticationError:
            logger.error("OpenRouter API key invalid for CV generation")
            raise ValueError("CV generation is not configured. Please contact support.")
        except RateLimitError:
            logger.warning("OpenRouter rate limit hit during CV generation")
            raise ValueError("CV generation is temporarily busy. Please try again in a minute.")
        except APIError as e:
            logger.error(f"OpenRouter API error during CV generation: {e}")
            raise ValueError("CV generation is temporarily unavailable. Please try again later.")

    return await asyncio.to_thread(_call)
