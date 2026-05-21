"""Normalize plain job descriptions to Markdown for frontend rendering."""
from __future__ import annotations

import re

_CAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9\s/&-]{7,}:?\s*$")
_BULLET_RE = re.compile(r"^[\s]*[•·\-*]\s+")
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])"
)
_URL_RE = re.compile(r"(https?://[^\s<>\"']+)")


def _line_is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _CAPS_HEADING_RE.match(stripped):
        return True
    if stripped.endswith(":") and len(stripped) <= 80 and stripped == stripped.upper():
        return True
    return False


def description_to_markdown(description: str | None) -> str:
    """Convert scraper plain text to lightweight Markdown."""
    if not description:
        return ""

    lines = description.replace("\r\n", "\n").split("\n")
    out: list[str] = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        if _BULLET_RE.match(line):
            bullet = _BULLET_RE.sub("", line).strip()
            out.append(f"- {bullet}")
            continue
        if _line_is_heading(line):
            title = line.strip().rstrip(":").strip()
            out.append(f"## {title}")
            continue
        out.append(line)

    text = "\n".join(out).strip()
    text = _URL_RE.sub(r"<\1>", text)
    text = _EMAIL_RE.sub(r"[\1](mailto:\1)", text)
    return text
