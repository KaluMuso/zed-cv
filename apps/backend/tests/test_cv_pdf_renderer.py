"""Tests for server-side CV PDF rendering."""
from app.schemas.cv_scratch import (
    BuildFromScratchBody,
    ScratchBasics,
    ScratchEducation,
    ScratchExperience,
    ScratchStyle,
)
from app.services.cv_pdf_renderer import render_cv_html, render_cv_pdf


def _sample_body() -> BuildFromScratchBody:
    return BuildFromScratchBody(
        summary=(
            "ICAZ-qualified accountant with 8+ years in banking and audit. "
            "Experienced in IFRS reporting and stakeholder management."
        ),
        basics=ScratchBasics(
            full_name="Chanda Banda",
            phone="+260971234567",
            email="chanda.banda@email.com",
            location="Lusaka, Zambia",
            headline="Chartered Accountant · IFRS",
        ),
        experience=[
            ScratchExperience(
                title="Senior Accountant",
                company="ZANACO",
                location="Lusaka",
                start_date="Jan 2019",
                end_date="Present",
                achievements=[
                    "Led month-end close for 12 branches, reducing cycle time by 18%.",
                    "Prepared IFRS-aligned statements with zero material findings.",
                ],
            )
        ],
        education=[
            ScratchEducation(
                degree="Bachelor of Accountancy",
                institution="University of Zambia",
                location="Lusaka",
                start_date="2011",
                end_date="2014",
                gpa="Distinction",
            )
        ],
        skills=["IFRS", "Excel", "SAP"],
        style=ScratchStyle(template="modern", accent_color="#0E5C3A"),
    )


def test_render_cv_html_includes_sections():
    html = render_cv_html(_sample_body())
    assert "Chanda Banda" in html
    assert "Senior Accountant" in html
    assert "University of Zambia" in html
    assert "IFRS" in html


def test_render_cv_pdf_produces_bytes_under_five_seconds():
    pdf_bytes, render_ms = render_cv_pdf(_sample_body())
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000
    assert render_ms < 5000
