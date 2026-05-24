"""Legal-docs API (task #62).

Two surfaces:

  - PUBLIC  GET  /api/v1/legal/{slug}        — read for the /legal/<slug>
                                               renderer's DB-fallback path.
                                               Returns 404 when no row exists
                                               so the frontend knows to fall
                                               back to the inline _content.ts.

  - ADMIN   GET  /api/v1/admin/legal/{slug}  — read for the WYSIWYG editor.
            PATCH /api/v1/admin/legal/{slug} — receive markdown, sanitise +
                                               convert to HTML server-side,
                                               upsert the row.

The admin write path is the trust boundary: content_md gets a raw-HTML
strip (markdown allows inline HTML, which is the XSS vector), gets
rendered to HTML with the `markdown` library, and that HTML is then
sanitised with `bleach`. Two layers, both server-side, both running
before the row lands in storage.

Slug whitelist is `{"privacy", "terms", "cookies", "refund"}` — the editor can't
create new legal pages from the API; routing is owned by code under
apps/frontend/src/app/legal/<slug>/page.tsx.
"""
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

import bleach
import markdown as md_lib
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.core.deps import get_supabase, require_admin

logger = logging.getLogger(__name__)

# Two routers: a public one mounted at /legal and an admin one mounted
# at /admin/legal. Keeping them separate makes the audit log (and the
# require_admin dep) explicit per request rather than having the same
# handler branch on the caller's role.
public_router = APIRouter(prefix="/legal", tags=["Legal"])
admin_router = APIRouter(
    prefix="/admin/legal", tags=["Admin"], dependencies=[Depends(require_admin)]
)


# Allowed slugs. Matches /apps/frontend/src/app/legal/<slug>/ directories.
LegalSlug = Literal["privacy", "terms", "cookies", "refund"]
_ALLOWED_SLUGS = {"privacy", "terms", "cookies", "refund"}


# ── sanitiser policy ──
# The set of tags + attributes the markdown library can plausibly emit
# from clean markdown. Anything outside this set is stripped by bleach.
# Notably: no <script>, <style>, <iframe>, no event handlers (on*), no
# inline javascript: URLs. h1-h6 + lists + emphasis + code + links is
# what legal copy actually needs.
_ALLOWED_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "strong", "em", "b", "i", "u",
    "a", "code", "pre", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "code": ["class"],
}
# Restrict link protocols. `mailto:` is a legitimate legal-page need
# (see existing privacy policy linking to convergeozambia@gmail.com).
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


# ── pydantic schemas ──
class LegalDoc(BaseModel):
    slug: str
    version: str
    content_md: str
    content_html: str
    last_modified_by: Optional[str] = None
    last_modified_at: Optional[str] = None


class LegalDocUpdate(BaseModel):
    """Body for PATCH /admin/legal/{slug}. content_md is the source of
    truth — the backend renders + sanitises HTML itself rather than
    trusting the client to."""

    version: str = Field(..., max_length=32)
    content_md: str = Field(..., min_length=1, max_length=100_000)


# ── helpers ──
def _validate_slug(slug: str) -> str:
    """Reject anything outside the slug whitelist with a clear 404."""
    if slug not in _ALLOWED_SLUGS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown legal slug: {slug}. Accepted: {sorted(_ALLOWED_SLUGS)}",
        )
    return slug


def _render_and_sanitise(content_md: str) -> str:
    """Convert markdown → HTML, then run bleach over the result.

    Returns the safe HTML string. The output of `markdown.markdown`
    can contain arbitrary inline HTML the user typed into the
    markdown source (markdown allows `<script>alert(1)</script>`
    verbatim by design); bleach is what stops that landing in storage.
    """
    raw_html = md_lib.markdown(
        content_md,
        extensions=["fenced_code", "tables"],
    )
    return bleach.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )


def _row_to_doc(row: dict) -> LegalDoc:
    """Normalise the DB row into the response schema. Defensive against
    missing fields so a partially-migrated row doesn't 500 the page."""
    return LegalDoc(
        slug=row["slug"],
        version=row.get("version") or "",
        content_md=row.get("content_md") or "",
        content_html=row.get("content_html") or "",
        last_modified_by=row.get("last_modified_by"),
        last_modified_at=row.get("last_modified_at"),
    )


# ── public read ──
@public_router.get("/{slug}", response_model=LegalDoc)
async def get_public_legal_doc(
    slug: str = Path(..., description="One of: privacy, terms, cookies, refund"),
    supabase=Depends(get_supabase),
) -> LegalDoc:
    """Public read for the /legal/<slug> page renderer's DB-fallback path.

    Returns 404 when no row exists in legal_docs for this slug — the
    frontend renderer reads that as "fall back to the inline
    _content.ts constants" rather than as a user-facing error.
    """
    _validate_slug(slug)
    res = (
        supabase.table("legal_docs")
        .select("*")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail=f"No DB row for {slug}")
    return _row_to_doc(res.data[0])


# ── admin read ──
@admin_router.get("/{slug}", response_model=LegalDoc)
async def get_admin_legal_doc(
    slug: str = Path(..., description="One of: privacy, terms, cookies, refund"),
    supabase=Depends(get_supabase),
) -> LegalDoc:
    """Admin read for the WYSIWYG editor. Same shape as the public
    endpoint — but on miss returns an empty doc rather than 404 so
    the editor opens cleanly on a slug that's never been saved yet.
    """
    _validate_slug(slug)
    res = (
        supabase.table("legal_docs")
        .select("*")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if res.data:
        return _row_to_doc(res.data[0])
    return LegalDoc(slug=slug, version="", content_md="", content_html="")


# ── admin write ──
@admin_router.patch("/{slug}", response_model=LegalDoc)
async def upsert_admin_legal_doc(
    body: LegalDocUpdate,
    slug: str = Path(..., description="One of: privacy, terms, cookies, refund"),
    current_user: dict = Depends(require_admin),
    supabase=Depends(get_supabase),
) -> LegalDoc:
    """Receive markdown from the editor; sanitise + render server-side;
    upsert the row.

    Trust boundary: NEVER stores the raw input verbatim. The HTML in
    legal_docs.content_html is always the bleach-cleaned output of the
    server-side markdown render, regardless of what the client sent."""
    _validate_slug(slug)
    content_html = _render_and_sanitise(body.content_md)

    payload = {
        "slug": slug,
        "version": body.version,
        "content_md": body.content_md,
        "content_html": content_html,
        "last_modified_by": current_user.get("id"),
        "last_modified_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert by slug so the second save replaces the first row in place
    # rather than ballooning into one-row-per-edit. The UNIQUE index on
    # slug makes on_conflict deterministic.
    res = (
        supabase.table("legal_docs")
        .upsert(payload, on_conflict="slug")
        .execute()
    )
    if not res.data:
        # Some supabase-py versions don't surface the upserted row on
        # the response. Re-fetch so the editor receives the canonical
        # post-save shape (including the auto-set last_modified_at).
        res = (
            supabase.table("legal_docs")
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Saved but could not re-read the row.",
            )

    logger.info(
        "legal_docs upsert: slug=%s by user=%s version=%s",
        slug,
        current_user.get("id"),
        body.version,
    )
    return _row_to_doc(res.data[0])
