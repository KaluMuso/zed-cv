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
from typing import Optional

from openai import OpenAI, AuthenticationError, RateLimitError, APIError
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings
from app.schemas.cv_sections import CVSections
from app.lib.retry import DEGRADED_LLM_USER_MESSAGE, circuit_is_open, degraded_llm_result
from app.services.openrouter_helpers import (
    create_chat_completion_with_retries,
    get_completion_content,
)

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


# Structured-JSON variant of the generator prompt (task #59).
# The LLM emits a CVSections-shaped JSON object so templates can render
# without a free-text reparse on the frontend. The flat fields above
# (CV_GENERATE_SYSTEM_PROMPT) are kept for the legacy `generate_cv()`
# path that callers still use for plain-text downloads / clipboards.
CV_GENERATE_STRUCTURED_SYSTEM_PROMPT = """You are an expert CV writer for the Zambian job market.

Rewrite the candidate's CV tailored to the target role. Keep it truthful — do not invent experience, qualifications, or achievements. Restructure, sharpen wording, surface the most relevant accomplishments for the target role, and quantify where the source CV supports it.

Output rules:
  - Return ONLY valid JSON, no preamble, no markdown fences.
  - Top-level keys: "header", "professional_summary", "work_experience", "education", "certifications", "languages", "projects", "achievements", "publications", "memberships", "volunteer_work", "references".
  - Omit any section the source CV doesn't have content for. Do not invent entries.
  - header: {linkedin_url, portfolio_url, github_url} (all optional URLs).
  - professional_summary.text: 1-3 sentences tailored to the target role.
  - work_experience[]: {title, company, location, start_date, end_date (or null for current), achievements: [string]}. Max 15 roles, max 20 achievements per role. Achievements lead with an action verb, surface quantified impact where the source supports it.
  - education[]: {degree, institution, location, start_date, end_date, gpa, thesis}. Max 10.
  - certifications[]: {name, issuer, year, expiry}. Max 25.
  - languages[]: {name, proficiency in "native"|"fluent"|"conversational"|"basic"}. Max 10.
  - projects[]: {name, role, technologies: [string], outcome}. Max 15.
  - achievements[]: {title, year}. Max 20.
  - publications[]: {title, venue, year, url}. Max 20.
  - memberships[]: {organisation, role, year_started, year_ended}. Max 15.
  - volunteer_work[]: {organisation, role, start_date, end_date, description}. Max 10.
  - references[]: {name, title, organisation, phone, email}. Max 6.

Date format: prefer "YYYY-MM"; "YYYY" if only year known; empty string if neither. Null for end_date on current roles.

Zambia-specific: recognize UNZA, CBU, Mulungushi, Cavendish, ZCAS, DMI as legitimate institutions. Don't penalise "Grade 12". Use +260 phone format. Recognize professional bodies: EIZ, ZICA, LAZ, ZIM, HPCZ, ZIHRM, ZIPS.
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
    if circuit_is_open():
        return degraded_llm_result(
            overall=0,
            strengths=[],
            improvements=[],
            summary=DEGRADED_LLM_USER_MESSAGE,
        )

    settings = get_settings()
    client = _client()

    def _call():
        try:
            response = create_chat_completion_with_retries(
                client,
                log_prefix="cv_generator",
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
            raw = get_completion_content(response, default="")
            if raw is None:
                logger.warning("cv_generator_analyze_skip: bad response: empty choices")
                raise ValueError("CV analysis service is temporarily unavailable. Please try again later.")
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


# Patterns the LLM produces when it refuses, errors, or echoes the prompt
# back instead of generating a real CV. Treated as validation failures so
# the user gets a clear error rather than a degenerate "CV" stored in
# cv_generations. Match is case-insensitive on the lowercased content.
_REFUSAL_OR_ECHO_MARKERS = (
    "i cannot help",
    "i can't help",
    "i'm unable to",
    "i am unable to",
    "i cannot generate",
    "as an ai language model",
    "--- candidate cv ---",      # echo of our system prompt's marker
    "--- target job description ---",
)


class GeneratedCV(BaseModel):
    """Validation for /cv/generate LLM output.

    Pinpoints the LLM-failure modes we've actually seen in prod:
    - empty / one-line responses (model gave up, hit max_tokens early)
    - the model refusing the task ("I cannot help with that...")
    - prompt-injection echo where the model dumps our system prompt back
    - silently truncated output that's plausibly a CV but only 2 sentences
    Anything that passes here is at least a viable rough draft worth
    storing in cv_generations.
    """

    content: str = Field(..., min_length=200, max_length=12000)
    word_count: int = Field(..., ge=50, le=2000)

    @field_validator("content", mode="after")
    @classmethod
    def _no_refusal_or_echo(cls, v: str) -> str:
        lowered = v.lower()
        for marker in _REFUSAL_OR_ECHO_MARKERS:
            if marker in lowered:
                raise ValueError(
                    f"Generated CV contains suspicious marker: {marker!r}. "
                    "The model may have refused the task or echoed the prompt."
                )
        return v


def _render_sections_to_text(
    sections: CVSections,
    *,
    full_name: str = "",
    contact_line: str = "",
) -> str:
    """Deterministic plain-text renderer for a CVSections object.

    Used by /cv/generate to keep storing a free-text representation in
    cv_generations.content (so the existing history view / copy-to-clipboard
    affordance keeps working) while the structured shape is the canonical
    one returned to the frontend.

    Format mirrors what the legacy `generate_cv()` LLM output produces so
    the frontend's parseCv.ts can still tokenise it on the legacy fallback
    path: blank line between sections, uppercase heading on its own line.
    """
    out: list[str] = []
    if full_name:
        out.append(full_name)
    if contact_line:
        out.append(contact_line)
    if out:
        out.append("")  # blank line before first section

    if sections.professional_summary and sections.professional_summary.text:
        out.append("SUMMARY")
        out.append(sections.professional_summary.text)
        out.append("")

    if sections.work_experience:
        out.append("EXPERIENCE")
        for w in sections.work_experience:
            dates = (w.start_date or "") + (f" – {w.end_date}" if w.end_date else " – Present")
            header = f"{w.title}, {w.company}"
            if w.location:
                header += f" ({w.location})"
            out.append(f"{header}  [{dates.strip()}]")
            for bullet in w.achievements:
                out.append(f"• {bullet}")
            out.append("")

    if sections.education:
        out.append("EDUCATION")
        for e in sections.education:
            line = f"{e.degree}, {e.institution}"
            if e.location:
                line += f" ({e.location})"
            dates = (e.start_date or "") + (f" – {e.end_date}" if e.end_date else "")
            if dates.strip(" –"):
                line += f"  [{dates.strip()}]"
            out.append(line)
            if e.gpa:
                out.append(f"  GPA: {e.gpa}")
            if e.thesis:
                out.append(f"  Thesis: {e.thesis}")
        out.append("")

    if sections.certifications:
        out.append("CERTIFICATIONS")
        for c in sections.certifications:
            line = c.name + (f" ({c.issuer})" if c.issuer else "")
            if c.year:
                line += f", {c.year}"
            out.append(f"• {line}")
        out.append("")

    if sections.languages:
        out.append("LANGUAGES")
        out.append(", ".join(f"{l.name} ({l.proficiency})" for l in sections.languages))
        out.append("")

    if sections.projects:
        out.append("PROJECTS")
        for p in sections.projects:
            line = p.name + (f" — {p.role}" if p.role else "")
            out.append(line)
            if p.outcome:
                out.append(f"  {p.outcome}")
            if p.technologies:
                out.append(f"  Stack: {', '.join(p.technologies)}")
        out.append("")

    if sections.achievements:
        out.append("ACHIEVEMENTS")
        for a in sections.achievements:
            out.append(f"• {a.title}" + (f" ({a.year})" if a.year else ""))
        out.append("")

    if sections.memberships:
        out.append("MEMBERSHIPS")
        for m in sections.memberships:
            dates = ""
            if m.year_started or m.year_ended:
                dates = f"  [{m.year_started or ''} – {m.year_ended or 'present'}]"
            out.append(f"• {m.organisation}, {m.role}{dates}")
        out.append("")

    if sections.publications:
        out.append("PUBLICATIONS")
        for p in sections.publications:
            line = p.title
            if p.venue:
                line += f" — {p.venue}"
            if p.year:
                line += f" ({p.year})"
            out.append(f"• {line}")
        out.append("")

    if sections.volunteer_work:
        out.append("VOLUNTEER WORK")
        for v in sections.volunteer_work:
            line = f"{v.role + ', ' if v.role else ''}{v.organisation}"
            out.append(f"• {line}")
            if v.description:
                out.append(f"  {v.description}")
        out.append("")

    if sections.references:
        out.append("REFERENCES")
        for r in sections.references:
            line = r.name + (f", {r.title}" if r.title else "")
            if r.organisation:
                line += f" — {r.organisation}"
            contacts = " · ".join(c for c in (r.phone, r.email) if c)
            if contacts:
                line += f"  ({contacts})"
            out.append(line)
    else:
        # Zambian convention: omit the section if no references are listed,
        # rather than emitting "References available on request" as a body
        # line. The TEMPLATES emit that line in the rendered CV. The text
        # representation we store is the structured source of truth and
        # should not carry rendering decisions.
        pass

    return "\n".join(out).rstrip() + "\n"


class GeneratedCVStructured(BaseModel):
    """Validation for /cv/generate structured-JSON output (task #59).

    Equivalent guards to GeneratedCV: the LLM occasionally refuses or
    echoes the prompt back inside one of the structured text fields.
    A pre-parse string-scan catches both before they land in storage.
    """
    sections: CVSections

    @field_validator("sections", mode="before")
    @classmethod
    def _scan_for_refusal(cls, v):
        """Reject the whole response if any text field contains a refusal
        or prompt-echo marker. We do this BEFORE shape validation so a
        garbage response can't slip through one corner."""
        try:
            blob = json.dumps(v, default=str).lower()
        except (TypeError, ValueError):
            return v
        for marker in _REFUSAL_OR_ECHO_MARKERS:
            if marker in blob:
                raise ValueError(
                    f"Generated CV contains suspicious marker: {marker!r}. "
                    "The model may have refused the task or echoed the prompt."
                )
        return v


async def generate_cv_structured(
    cv_text: str,
    job_title: str,
    company: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Produce a tailored CV in CVSections shape (task #59).

    Returns {sections: CVSections, content: str, word_count: int} so the
    /cv/generate endpoint can both return structured data to the frontend
    AND store a rendered text representation in cv_generations.content
    for backwards compat. Failures (too short, refusal, prompt-echo) raise
    ValueError which the endpoint maps to 503.
    """
    if circuit_is_open():
        return degraded_llm_result(
            sections=None,
            content=DEGRADED_LLM_USER_MESSAGE,
            word_count=0,
        )

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
            response = create_chat_completion_with_retries(
                client,
                log_prefix="cv_generator_structured",
                model=settings.llm_model,
                # 4096 to fit the structured shape; 1500 (used by the
                # plain-text path) frequently truncated mid-array.
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": CV_GENERATE_STRUCTURED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = get_completion_content(response, default="")
            if raw is None:
                logger.warning("cv_generator_skip: bad response: empty choices")
                raise ValueError("Empty response from CV generator")
            raw = raw.strip()
            if not raw:
                raise ValueError("Empty response from CV generator")
            raw_json = _strip_fences(raw).strip()
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                logger.error("Generator emitted non-JSON: preview=%r", raw[:200])
                raise ValueError(
                    "We couldn't produce a usable CV for this role. "
                    "Try a more specific job title or upload a fuller CV."
                )

            try:
                validated = GeneratedCVStructured(sections=data)
            except ValidationError as ve:
                logger.error(
                    "Structured CV failed validation: errors=%s preview=%r",
                    ve.errors()[:3], raw_json[:200],
                )
                raise ValueError(
                    "We couldn't produce a usable CV for this role. "
                    "Try a more specific job title or upload a fuller CV."
                )

            rendered = _render_sections_to_text(validated.sections)
            word_count = len(rendered.split())
            return {
                "sections": validated.sections,
                "content": rendered,
                "word_count": word_count,
            }
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


async def generate_cv(
    cv_text: str,
    job_title: str,
    company: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Produce a tailored CV draft for the target role.

    Output is validated through GeneratedCV — failures (too short, refusal,
    prompt-echo) raise ValueError which the upload route maps to 503/422.
    """
    if circuit_is_open():
        return degraded_llm_result(
            content=DEGRADED_LLM_USER_MESSAGE,
            word_count=0,
        )

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
            response = create_chat_completion_with_retries(
                client,
                log_prefix="cv_generator_prose",
                model=settings.llm_model,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": CV_GENERATE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = get_completion_content(response, default="")
            if content is None:
                logger.warning("cv_generator_prose_skip: bad response: empty choices")
                raise ValueError("Empty response from CV generator")
            content = content.strip()
            if not content:
                raise ValueError("Empty response from CV generator")

            raw_word_count = len(content.split())
            try:
                validated = GeneratedCV(content=content, word_count=raw_word_count)
            except ValidationError as ve:
                logger.error(
                    "Generated CV failed validation: errors=%s preview=%r",
                    ve.errors(), content[:200],
                )
                # Surface a user-facing message; the raw error stays in logs.
                raise ValueError(
                    "We couldn't produce a usable CV for this role. "
                    "Try a more specific job title or upload a fuller CV."
                )

            return {"content": validated.content, "word_count": validated.word_count}
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
