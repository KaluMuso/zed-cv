"""Role-title normalisation for the preferences auto-populate path.

The CV parser returns work-experience titles verbatim — "Senior Software
Engineer (2020-2023)", "Lead Data Analyst, Lusaka", "Marketing Manager
- Full-time". Used as-is they create a poor user_preferences.target_roles
entry (duplicates with seniority prefixes, embedded dates, location
slugs). This helper canonicalises one title to a clean form so we can
dedupe before writing.

Conservative by design: anything we can't confidently strip stays in.
Better to leave "Senior" attached than to mangle "Senior Counsel" into
"Counsel" when the seniority IS the job.
"""
from __future__ import annotations

import re

# Seniority prefixes we recognise. Order doesn't matter — applied as
# alternation. Only stripped when followed by a space and at least one
# more word (so "Senior" alone stays "Senior").
_SENIORITY_PREFIXES = (
    "senior",
    "snr",
    "sr",
    "junior",
    "jnr",
    "jr",
    "lead",
    "principal",
    "staff",
    "chief",
    "head",
    "assistant",
    "associate",
    "trainee",
    "graduate",
    "entry-level",
    "entry level",
    "mid-level",
    "mid level",
)

_SENIORITY_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _SENIORITY_PREFIXES) + r")\s+",
    re.IGNORECASE,
)

# Trailing parens or brackets used for year ranges, locations, employment
# type. Matches "(2020-2023)", "[Remote]", "(Lusaka)", "- Full-time".
_TRAILING_PAREN = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]\s*$")
_TRAILING_HYPHEN = re.compile(r"\s*[\-–—]\s+[^,]*$")

# Common employment-type / time-base suffixes appended after a comma.
# These are job-metadata, not part of the role name.
_EMPLOYMENT_SUFFIX_RE = re.compile(
    r",?\s*(full[-\s]?time|part[-\s]?time|contract|freelance|"
    r"intern(?:ship)?|temp(?:orary)?|remote|hybrid|on[-\s]?site|"
    r"permanent|fixed[-\s]?term)\b.*$",
    re.IGNORECASE,
)

# Year ranges anywhere in the string ("2020-2023", "2020 - present").
_YEAR_RANGE_RE = re.compile(
    r"\b(?:19|20)\d{2}\s*(?:-|to|until|–|—)\s*"
    r"(?:(?:19|20)\d{2}|present|current|date|now)\b",
    re.IGNORECASE,
)

# Standalone year — keep restrictive so "Web 2.0 Developer" doesn't
# get its "2.0" mistaken for a year. We only match 4-digit years
# matching 19xx/20xx and only when surrounded by whitespace.
_STANDALONE_YEAR_RE = re.compile(r"\s+\b(?:19|20)\d{2}\b")


def normalize_role_title(title: str) -> str:
    """Return a cleaned canonical form of `title`.

    Returns "" if `title` is empty / all noise after stripping. The
    output preserves the casing of the cleaned source (title-cased
    inputs stay title-cased) so the Preferences tab UI doesn't need
    to re-case anything for display.

    Examples
    --------
    >>> normalize_role_title("Senior Software Engineer (2020-2023)")
    'Software Engineer'
    >>> normalize_role_title("Lead Data Analyst, Lusaka")
    'Data Analyst, Lusaka'  # location stays; not a known suffix
    >>> normalize_role_title("Marketing Manager - Full-time")
    'Marketing Manager'
    >>> normalize_role_title("Software Engineer 2020-2023")
    'Software Engineer'
    >>> normalize_role_title("   ")
    ''
    """
    if not isinstance(title, str):
        return ""

    s = title.strip()
    if not s:
        return ""

    # Strip year ranges first so a "(2020-2023)" tail doesn't have to
    # be matched against the trailing-paren regex separately.
    s = _YEAR_RANGE_RE.sub("", s)
    s = _STANDALONE_YEAR_RE.sub("", s)

    # Repeatedly strip trailing brackets/parens because some inputs
    # carry two ("(2020-2023) (Remote)"). One pass per regex would
    # leave the second one in.
    for _ in range(3):
        new = _TRAILING_PAREN.sub("", s).strip()
        if new == s:
            break
        s = new

    # Trailing employment-type suffix ("Marketing Manager - Full-time"
    # → "Marketing Manager"). Has to come BEFORE the generic trailing-
    # hyphen strip below, because that one is too aggressive on its own.
    s = _EMPLOYMENT_SUFFIX_RE.sub("", s).strip()

    # Strip seniority prefix. Loop in case the title nested prefixes
    # ("Senior Junior Engineer" — unlikely but cheap to guard against).
    for _ in range(3):
        new = _SENIORITY_RE.sub("", s, count=1).strip()
        if new == s or not new:
            break
        s = new

    # Cleanup: collapse repeated whitespace, strip dangling punctuation.
    s = re.sub(r"\s+", " ", s).strip(" -,;:")
    return s


def normalize_role_titles(titles: list[str]) -> list[str]:
    """Apply `normalize_role_title` to each entry, dedupe, preserve order.

    Used by the auto-populate path to convert the parsed
    work_experience job titles into a deduplicated target_roles list.
    Dedup is case-insensitive — "Software Engineer" and "software
    engineer" are the same role.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in titles:
        norm = normalize_role_title(raw)
        if not norm:
            continue
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out
