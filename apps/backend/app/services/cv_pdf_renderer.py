"""Server-side CV PDF rendering via WeasyPrint."""
from __future__ import annotations

import html
import re
import time
from typing import Literal

from weasyprint import CSS, HTML

from app.schemas.cv_scratch import (
    BuildFromScratchBody,
    ScratchEducation,
    ScratchExperience,
)

TemplateName = Literal["modern", "classic", "compact"]


def _esc(text: str) -> str:
    return html.escape(text or "")


def _contact_line(body: BuildFromScratchBody) -> str:
    bits = [body.basics.phone, body.basics.email, body.basics.location]
    return " · ".join(_esc(b.strip()) for b in bits if b and b.strip())


def _role_dates(role: ScratchExperience) -> str:
    parts = [role.start_date.strip(), role.end_date.strip() or "Present"]
    joined = " – ".join(p for p in parts if p)
    return _esc(joined)


def _edu_dates(edu: ScratchEducation) -> str:
    parts = [edu.start_date.strip(), edu.end_date.strip()]
    joined = " – ".join(p for p in parts if p)
    return _esc(joined)


def _render_experience_block(experience: list[ScratchExperience]) -> str:
    if not experience:
        return ""
    blocks: list[str] = []
    for role in experience:
        if not role.title.strip() and not role.company.strip():
            continue
        loc = f" ({_esc(role.location)})" if role.location.strip() else ""
        dates = _role_dates(role)
        date_suffix = f" [{dates}]" if dates else ""
        bullets = "".join(
            f"<li>{_esc(b)}</li>" for b in role.achievements if b.strip()
        )
        bullet_html = f"<ul>{bullets}</ul>" if bullets else ""
        blocks.append(
            f"""<div class="role-block">
  <p class="entry-title"><strong>{_esc(role.title)}</strong>, {_esc(role.company)}{loc}{date_suffix}</p>
  {bullet_html}
</div>"""
        )
    if not blocks:
        return ""
    return f"<section><h2>Experience</h2>{''.join(blocks)}</section>"


def _render_education_block(education: list[ScratchEducation]) -> str:
    if not education:
        return ""
    lines: list[str] = []
    for edu in education:
        if not edu.degree.strip() and not edu.institution.strip():
            continue
        loc = f" ({_esc(edu.location)})" if edu.location.strip() else ""
        dates = _edu_dates(edu)
        date_suffix = f" [{dates}]" if dates else ""
        gpa = f'<span class="gpa">GPA: {_esc(edu.gpa)}</span>' if edu.gpa.strip() else ""
        lines.append(
            f"""<p class="entry-title"><strong>{_esc(edu.degree)}</strong>, """
            f"""{_esc(edu.institution)}{loc}{date_suffix}{gpa}</p>"""
        )
    if not lines:
        return ""
    return f"<section><h2>Education</h2>{''.join(lines)}</section>"


def _render_skills_block(skills: list[str]) -> str:
    cleaned = [s.strip() for s in skills if s.strip()]
    if not cleaned:
        return ""
    joined = " · ".join(_esc(s) for s in cleaned)
    return f"<section><h2>Skills</h2><p class=\"skills-line\">{joined}</p></section>"


def _base_css(accent: str, template: TemplateName) -> str:
    accent_safe = accent if re.fullmatch(r"#[0-9A-Fa-f]{6}", accent or "") else "#0E5C3A"
    font_body = "Georgia, 'Times New Roman', serif"
    font_modern = "'Helvetica Neue', Arial, sans-serif"
    if template == "modern":
        body_font = font_modern
        h1_size = "22pt"
        section_style = f"border-left: 3pt solid {accent_safe}; padding-left: 10pt;"
    elif template == "compact":
        body_font = font_modern
        h1_size = "18pt"
        section_style = "margin-top: 8pt;"
    else:
        body_font = font_body
        h1_size = "20pt"
        section_style = ""

    page_margin = "12mm 14mm" if template == "compact" else "14mm 16mm"
    body_size = "9pt" if template == "compact" else "10pt"

    return f"""
@page {{
  size: A4;
  margin: {page_margin};
}}
body {{
  font-family: {body_font};
  font-size: {body_size};
  line-height: 1.45;
  color: #15140f;
}}
h1 {{
  font-size: {h1_size};
  margin: 0 0 4pt;
  color: {accent_safe};
}}
.headline {{
  font-size: 11pt;
  font-weight: 600;
  margin: 0 0 6pt;
  color: #3a382f;
}}
.contact {{
  font-size: 9pt;
  color: #6f6a5c;
  margin-bottom: 12pt;
}}
section {{
  {section_style}
  margin-bottom: 10pt;
  page-break-inside: avoid;
}}
h2 {{
  font-size: 10pt;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 6pt;
  padding-bottom: 2pt;
  border-bottom: 1pt solid #d8cebb;
  color: {accent_safe};
}}
p {{ margin: 0 0 6pt; }}
ul {{ margin: 0 0 8pt; padding-left: 1.2em; }}
li {{ margin-bottom: 2pt; }}
.role-block {{ margin-bottom: 8pt; page-break-inside: avoid; }}
.entry-title {{ margin-bottom: 2pt; }}
.skills-line {{ font-size: 9.5pt; }}
.gpa {{ display: block; font-size: 9pt; color: #6f6a5c; }}
.summary {{ margin-bottom: 10pt; }}
"""


def render_cv_html(body: BuildFromScratchBody) -> str:
    """Build print-ready HTML for a scratch CV."""
    summary_html = ""
    if body.style.show_summary and body.summary.strip():
        summary_html = (
            f'<section class="summary"><h2>Summary</h2>'
            f"<p>{_esc(body.summary.strip())}</p></section>"
        )

    headline_html = (
        f'<p class="headline">{_esc(body.basics.headline)}</p>'
        if body.basics.headline.strip()
        else ""
    )
    contact = _contact_line(body)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{_esc(body.basics.full_name)} CV</title></head>
<body>
  <header>
    <h1>{_esc(body.basics.full_name)}</h1>
    {headline_html}
    {f'<div class="contact">{contact}</div>' if contact else ''}
  </header>
  {summary_html}
  {_render_experience_block(body.experience)}
  {_render_education_block(body.education)}
  {_render_skills_block(body.skills)}
</body>
</html>"""


def render_cv_pdf(body: BuildFromScratchBody) -> tuple[bytes, int]:
    """Render CV to PDF bytes. Returns (pdf_bytes, render_time_ms)."""
    started = time.perf_counter()
    html_content = render_cv_html(body)
    css = CSS(string=_base_css(body.style.accent_color, body.style.template))
    pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css])
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return pdf_bytes, elapsed_ms
