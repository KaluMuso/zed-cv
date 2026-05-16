"""Pin the LLM-friendly nullability contract on CVSections sub-models.

Production prod /cv/upload was returning 503 because the LLM's structured
output occasionally emits explicit JSON `null` for optional location /
start_date / issuer fields. Pydantic v2 rejects null on plain `str`-typed
fields with a `string_type` error even when the field has a default —
defaults only apply when the key is missing entirely. The schemas were
relaxed to `Optional[str]` to match what the LLM actually sends and what
the frontend type already declares (`location?: string` etc.).

These tests pin the new contract so the next refactor doesn't accidentally
re-tighten the type and reintroduce the 503.
"""
from app.schemas.cv_sections import (
    Certification,
    CVSections,
    Education,
    ProfessionalSummary,
    WorkExperience,
)
from app.services.cv_generator import _render_sections_to_text


class TestOptionalFields:
    """The fields the LLM was sending null for must accept None directly."""

    def test_work_experience_accepts_none_location(self):
        w = WorkExperience(
            title="Engineer", company="Acme", location=None, start_date=None
        )
        assert w.location is None
        assert w.start_date is None

    def test_education_accepts_none_location(self):
        e = Education(
            degree="BSc", institution="UNZA", location=None, start_date=None
        )
        assert e.location is None
        assert e.start_date is None

    def test_certification_accepts_none_issuer(self):
        c = Certification(name="AWS SAA", issuer=None)
        assert c.issuer is None


class TestProfessionalSummaryCap:
    """The 1000-char cap was the original 503; 5000 is the new ceiling."""

    def test_accepts_text_at_new_cap(self):
        s = ProfessionalSummary(text="x" * 5000)
        assert len(s.text) == 5000

    def test_rejects_text_over_new_cap(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfessionalSummary(text="x" * 5001)


class TestLLMNullPayloadValidates:
    """End-to-end shape pinned: an LLM payload that mirrors the failing
    prod traceback (explicit nulls on the now-optional fields) must
    validate as a complete CVSections without raising."""

    def test_llm_style_payload_with_nulls_validates(self):
        payload = {
            "professional_summary": {"text": "Senior dev with 12 years."},
            "work_experience": [
                {
                    "title": "Senior Engineer",
                    "company": "Acme Zambia",
                    "location": None,
                    "start_date": None,
                    "end_date": None,
                    "achievements": ["Shipped X"],
                }
            ],
            "education": [
                {
                    "degree": "BSc Computer Science",
                    "institution": "UNZA",
                    "location": None,
                    "start_date": None,
                    "end_date": "2018",
                }
            ],
            "certifications": [
                {"name": "AWS Solutions Architect", "issuer": None, "year": "2022"}
            ],
        }
        sections = CVSections.model_validate(payload)
        assert sections.work_experience[0].location is None
        assert sections.education[0].start_date is None
        assert sections.certifications[0].issuer is None


class TestGeneratorHandlesNoneDates:
    """Regression guard for the cv_generator concatenation sites.

    `start_date or ""` was added at the two `dates = w.start_date + ...`
    lines so the renderer doesn't TypeError on the new None-valued fields.
    """

    def test_renderer_does_not_typeerror_on_none_dates(self):
        sections = CVSections.model_validate(
            {
                "work_experience": [
                    {
                        "title": "Engineer",
                        "company": "Acme",
                        "location": None,
                        "start_date": None,
                        "achievements": ["Built it"],
                    }
                ],
                "education": [
                    {
                        "degree": "BSc",
                        "institution": "UNZA",
                        "location": None,
                        "start_date": None,
                    }
                ],
            }
        )
        # The function is private but importable; the assertion is just
        # "this doesn't raise". A failing test here is a real regression
        # of the prod TypeError this PR was written to prevent.
        text = _render_sections_to_text(sections)
        assert "EXPERIENCE" in text
        assert "EDUCATION" in text
