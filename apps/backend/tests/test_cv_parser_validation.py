"""Unit tests for CVParseResult — the Pydantic schema that validates and
coerces LLM output before it lands in `cvs.parsed_data`.

The LLM frequently returns slightly-wrong shapes (strings instead of
arrays, dicts inside skill arrays, "5+ years" as years_experience).
These tests pin the tolerant-coercion behavior so a future "let's just
trust the LLM" refactor can't regress past failures back into prod.
"""
import pytest
from pydantic import ValidationError

from app.services.cv_parser import CVParseResult, validate_cv_parse_raw
from app.schemas.cv_sections import (
    CVSections,
    WorkExperience,
    Education,
    Certification,
    Language,
    Project,
    Achievement,
    Publication,
    Membership,
    VolunteerWork,
    Reference,
    CVHeader,
    ProfessionalSummary,
    MAX_WORK_EXPERIENCE,
    MAX_ACHIEVEMENTS_PER_ROLE,
    MAX_CERTIFICATIONS,
    MAX_PROJECT_TECHNOLOGIES,
)


class TestSkillsCoercion:
    def test_normal_lowercase_array(self):
        r = CVParseResult(skills=["python", "sql"])
        assert r.skills == ["python", "sql"]

    def test_mixed_case_deduplicates_after_lowercasing(self):
        r = CVParseResult(skills=["Python", "python", "PYTHON", "SQL"])
        assert r.skills == ["python", "sql"]

    def test_array_of_dicts_with_name_field(self):
        # Real LLM output we've seen: [{"name": "react", "level": "advanced"}]
        r = CVParseResult(skills=[{"name": "react", "level": "advanced"}, {"name": "node"}])
        assert r.skills == ["react", "node"]

    def test_single_string_instead_of_array(self):
        # LLM occasionally drops the array wrapper
        r = CVParseResult(skills="python")
        assert r.skills == ["python"]

    def test_drops_null_and_empty(self):
        r = CVParseResult(skills=["python", None, "", "  "])
        assert r.skills == ["python"]

    def test_handles_completely_missing(self):
        r = CVParseResult()
        assert r.skills == []


class TestYearsExperienceCoercion:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            (5, 5),
            ("5", 5),
            ("5 years", 5),
            ("5+", 5),
            ("5.7", 5),
            (5.0, 5),
            (None, 0),
            ("", 0),
            ("a lot", 0),
            (-3, 0),       # clamp negative
            (999, 80),     # clamp absurd
            ("100", 80),
        ],
    )
    def test_lenient_coercion(self, raw, expected):
        r = CVParseResult(years_experience=raw)
        assert r.years_experience == expected


class TestConfidenceCoercion:
    def test_normalizes_0_to_100_scale(self):
        # LLM occasionally returns 85 instead of 0.85
        r = CVParseResult(confidence=85)
        assert r.confidence == 0.85

    def test_passes_through_0_to_1(self):
        r = CVParseResult(confidence=0.92)
        assert r.confidence == 0.92

    def test_clamps_above_1(self):
        # Already-scaled but over 100 -> still clamped
        r = CVParseResult(confidence=200)
        assert r.confidence == 1.0

    def test_string_input(self):
        r = CVParseResult(confidence="0.5")
        assert r.confidence == 0.5

    def test_missing_defaults_to_zero(self):
        r = CVParseResult()
        assert r.confidence == 0.0


class TestRequiredFieldsAreNotRequired:
    """All fields have safe defaults — a totally-empty LLM response
    should still produce a valid model, not 422 the whole upload."""

    def test_empty_dict_is_valid(self):
        r = CVParseResult()
        assert r.full_name == ""
        assert r.email is None
        assert r.phone is None
        assert r.years_experience == 0
        assert r.confidence == 0.0

    def test_rejects_genuinely_bad_types(self):
        # full_name as a deeply-nested object is not coercible — bail.
        with pytest.raises(ValidationError):
            CVParseResult(full_name={"deeply": {"nested": "thing"}})


class TestEducationCoercion:
    def test_array_of_strings(self):
        r = CVParseResult(education=["BSc UNZA", "Grade 12"])
        assert r.education == ["BSc UNZA", "Grade 12"]

    def test_array_of_dicts(self):
        r = CVParseResult(
            education=[{"name": "BSc Computer Science"}, {"title": "Grade 12"}]
        )
        assert r.education == ["BSc Computer Science", "Grade 12"]

    def test_education_is_NOT_lowercased(self):
        # skills are lowercased (dedupe key), education is human-readable
        r = CVParseResult(education=["BSc Computer Science"])
        assert r.education == ["BSc Computer Science"]


# ─── task #59: structured CVSections ──────────────────────────────────


class TestCVSectionsOnCVParseResult:
    """The new sections key must be optional and backwards-compatible
    so legacy parsed_data rows (no `sections` key) still validate."""

    def test_legacy_parsed_data_without_sections_still_validates(self):
        r = CVParseResult(full_name="Mwape Phiri", skills=["python"])
        assert r.sections is None

    def test_empty_sections_dict_coerced_to_none(self):
        # Wasteful storage; normalize {} → None so we don't pollute jsonb.
        r = CVParseResult(sections={})
        assert r.sections is None

    def test_explicit_none_stays_none(self):
        r = CVParseResult(sections=None)
        assert r.sections is None

    def test_partial_sections_validate(self):
        r = CVParseResult(
            sections={
                "professional_summary": {"text": "Senior backend engineer."},
                "work_experience": [
                    {
                        "title": "Backend Engineer",
                        "company": "Airtel Zambia",
                        "location": "Lusaka",
                        "start_date": "2020-03",
                        "end_date": None,
                        "achievements": ["Cut p99 latency from 800ms to 120ms"],
                    }
                ],
            }
        )
        assert r.sections is not None
        assert r.sections.professional_summary.text.startswith("Senior")
        assert len(r.sections.work_experience) == 1
        assert r.sections.work_experience[0].end_date is None  # current role

    def test_fully_populated_sections_round_trip(self):
        r = CVParseResult(
            sections={
                "header": {"linkedin_url": "https://www.linkedin.com/in/mphiri"},
                "professional_summary": {"text": "Backend engineer."},
                "work_experience": [
                    {"title": "Eng", "company": "Acme", "achievements": ["did x"]}
                ],
                "education": [
                    {"degree": "BSc CS", "institution": "UNZA", "start_date": "2014"}
                ],
                "certifications": [{"name": "AWS SAA", "issuer": "AWS", "year": "2023"}],
                "languages": [{"name": "English", "proficiency": "native"}],
                "projects": [{"name": "zedcv", "outcome": "shipped"}],
                "achievements": [{"title": "Hackathon winner", "year": "2022"}],
                "publications": [{"title": "On Latency", "venue": "ACM"}],
                "memberships": [{"organisation": "EIZ", "role": "Member"}],
                "volunteer_work": [
                    {"organisation": "Code for Zambia", "description": "mentored"}
                ],
                "references": [{"name": "Dr Banda", "organisation": "UNZA"}],
            }
        )
        s = r.sections
        assert s is not None
        assert str(s.header.linkedin_url).startswith("https://www.linkedin.com/in/")
        assert len(s.languages) == 1


class TestWorkExperienceCaps:
    def test_caps_at_max_work_experience(self):
        # LLM occasionally pads with duplicates / fabricated roles. Cap defends.
        many = [
            {"title": "Eng", "company": "Co", "achievements": []}
            for _ in range(MAX_WORK_EXPERIENCE + 5)
        ]
        s = CVSections(work_experience=many)
        assert len(s.work_experience) == MAX_WORK_EXPERIENCE

    def test_caps_achievements_per_role(self):
        bullets = [f"achievement #{i}" for i in range(MAX_ACHIEVEMENTS_PER_ROLE + 10)]
        w = WorkExperience(title="Eng", company="Co", achievements=bullets)
        assert len(w.achievements) == MAX_ACHIEVEMENTS_PER_ROLE

    def test_achievements_drops_empty_strings(self):
        w = WorkExperience(title="Eng", company="Co", achievements=["ok", "", "  ", None])
        assert w.achievements == ["ok"]

    def test_achievement_string_truncated_at_500(self):
        long = "x" * 1000
        w = WorkExperience(title="Eng", company="Co", achievements=[long])
        assert len(w.achievements[0]) == 500

    def test_required_title_and_company(self):
        with pytest.raises(ValidationError):
            WorkExperience(company="Co")
        with pytest.raises(ValidationError):
            WorkExperience(title="Eng")


class TestEducationStructured:
    def test_minimal_education_validates(self):
        e = Education(degree="BSc CS", institution="UNZA")
        assert e.gpa is None
        assert e.thesis is None

    def test_thesis_max_length_enforced(self):
        too_long = "x" * 600
        with pytest.raises(ValidationError):
            Education(degree="BSc", institution="UNZA", thesis=too_long)


class TestCertification:
    def test_minimal(self):
        c = Certification(name="AWS SAA")
        assert c.year is None

    def test_caps_certifications(self):
        many = [{"name": f"Cert {i}"} for i in range(MAX_CERTIFICATIONS + 5)]
        s = CVSections(certifications=many)
        assert len(s.certifications) == MAX_CERTIFICATIONS


class TestLanguageProficiencyLiteral:
    def test_accepts_known_values(self):
        for p in ("native", "fluent", "conversational", "basic"):
            assert Language(name="English", proficiency=p).proficiency == p

    def test_rejects_unknown_proficiency(self):
        # LLM occasionally invents levels — must reject so storage stays clean.
        with pytest.raises(ValidationError):
            Language(name="English", proficiency="expert")


class TestProjectTechnologies:
    def test_dedupe_case_insensitive(self):
        p = Project(name="zedcv", technologies=["Python", "python", "PYTHON", "Postgres"])
        assert p.technologies == ["Python", "Postgres"]

    def test_caps_technologies(self):
        techs = [f"tech-{i}" for i in range(MAX_PROJECT_TECHNOLOGIES + 5)]
        p = Project(name="x", technologies=techs)
        assert len(p.technologies) == MAX_PROJECT_TECHNOLOGIES

    def test_drops_empty_and_none(self):
        p = Project(name="x", technologies=["python", "", None, "  "])
        assert p.technologies == ["python"]


class TestPublicationUrl:
    def test_valid_url_accepted(self):
        p = Publication(title="Paper", url="https://arxiv.org/abs/2401.0001")
        assert p.url is not None

    def test_garbage_url_rejected(self):
        with pytest.raises(ValidationError):
            Publication(title="Paper", url="not-a-url")


class TestMembership:
    def test_default_role_is_member(self):
        # Zambian CVs often list "EIZ" without a role — default to "Member"
        # so the rendered output isn't blank.
        m = Membership(organisation="EIZ")
        assert m.role == "Member"


class TestVolunteerWork:
    def test_minimal(self):
        v = VolunteerWork(organisation="Code for Zambia")
        assert v.role == ""
        assert v.description == ""


class TestReference:
    def test_minimal(self):
        r = Reference(name="Dr Banda")
        assert r.title == ""
        assert r.phone is None


class TestCVHeader:
    def test_all_optional(self):
        h = CVHeader()
        assert h.linkedin_url is None
        assert h.portfolio_url is None
        assert h.github_url is None

    def test_garbage_url_rejected(self):
        # Bad URL on one field shouldn't sneak through.
        with pytest.raises(ValidationError):
            CVHeader(linkedin_url="not a url")


class TestProfessionalSummary:
    def test_caps_text_length(self):
        # Cap was raised from 1000 to 5000 to fit long-form CV summaries
        # the LLM was producing; the cap still exists to bound runaway.
        too_long = "x" * 5500
        with pytest.raises(ValidationError):
            ProfessionalSummary(text=too_long)

    def test_default_empty(self):
        s = ProfessionalSummary()
        assert s.text == ""


# Shape from Sentry ZEDCV-BACKEND-N (Sylvia Nkumbwa): flat fields valid;
# sections had string references, string education rows, and dict dates.
SYLVIA_BACKEND_N_RAW = {
    "full_name": "Sylvia Nkumbwa",
    "email": "sylvia.nkumbwa@example.com",
    "phone": "+260971234567",
    "location": "Lusaka, Zambia",
    "years_experience": 3,
    "skills": [
        "laboratory management",
        "atomic absorption spectrometry",
        "aas",
        "quality control",
        "iso 17025",
    ],
    "experience_summary": (
        "Laboratory professional with experience in atomic absorption "
        "spectrometry and quality systems."
    ),
    "education": ["BSc Chemistry, University of Zambia"],
    "confidence": 0.88,
    "sections": {
        "professional_summary": {
            "text": "Dedicated laboratory scientist based in Lusaka.",
        },
        "work_experience": [
            {
                "title": "Laboratory Analyst",
                "company": "Zambia Bureau of Standards",
                "location": "Lusaka",
                "start_date": {"year": 2022, "month": 1},
                "end_date": "Present",
                "achievements": ["Maintained ISO 17025 compliance"],
            }
        ],
        "education": [
            "BSc Chemistry, University of Zambia",
        ],
        "references": [
            "Mr. Banda, Quality Manager, ZABS",
            "Dr. Phiri, University of Zambia",
        ],
        "languages": [{"name": "English", "proficiency": "fluent"}],
    },
}


class TestCVSectionsCoercion:
    def test_work_experience_bare_string_becomes_title(self):
        s = CVSections(work_experience=["Senior Analyst at ZABS"])
        assert len(s.work_experience) == 1
        assert s.work_experience[0].title == "Senior Analyst at ZABS"
        assert s.work_experience[0].company == ""

    def test_education_string_becomes_degree(self):
        s = CVSections(education=["BSc Chemistry, UNZA"])
        assert s.education[0].degree == "BSc Chemistry, UNZA"
        assert s.education[0].institution == ""

    def test_references_string_becomes_name(self):
        s = CVSections(references=["Dr. Banda, UNZA"])
        assert s.references[0].name == "Dr. Banda, UNZA"

    def test_work_experience_dict_date_coerced(self):
        w = WorkExperience(
            title="Analyst",
            company="ZABS",
            start_date={"year": 2022, "month": 1},
            end_date="Present",
        )
        assert w.start_date == "2022-01"
        assert w.end_date is None


class TestValidateCvParseRaw:
    def test_sylvia_backend_n_payload_parses_without_error(self):
        r = validate_cv_parse_raw(SYLVIA_BACKEND_N_RAW)
        assert r.full_name == "Sylvia Nkumbwa"
        assert "laboratory management" in r.skills
        assert r.education == ["BSc Chemistry, University of Zambia"]
        assert r.sections is not None
        assert len(r.sections.work_experience) == 1
        assert r.sections.work_experience[0].start_date == "2022-01"
        assert len(r.sections.references) == 2
        assert r.sections.references[0].name.startswith("Mr. Banda")

    def test_lenient_parse_keeps_flat_when_one_section_invalid(self):
        raw = {
            **{k: v for k, v in SYLVIA_BACKEND_N_RAW.items() if k != "sections"},
            "sections": {
                "header": {"linkedin_url": "not-a-valid-url"},
                "languages": [{"name": "English", "proficiency": "fluent"}],
            },
        }
        r = validate_cv_parse_raw(raw)
        assert r.full_name == "Sylvia Nkumbwa"
        assert r.sections is not None
        assert len(r.sections.languages) == 1
        assert r.sections.header is None
