"""Forwardable match cards: shareable public previews + referral attribution.

Flow:
  1. POST /api/v1/matches/{match_id}/share  (auth) —
     Sender generates (or reuses) a share token for one of their matches.
     Returns the canonical share URL the sender forwards to friends.

  2. GET  /api/v1/match-cards/{token}        (public, no auth) —
     Recipient's client (or the /m/<token> SSR page) fetches the blurred
     preview. The endpoint also increments view_count via an RPC.

Attribution flows through the existing referral system:
  - The public card includes the sender's referral_code.
  - The frontend's /m/<token> page links to /auth?ref=<referral_code>.
  - The auth flow's attach_referral_on_signup binds the new user to the
    sender, and the existing referral_events / qualified / rewarded
    pipeline handles the +5 matches reward when the referred user uploads
    a CV.
"""
from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.deps import get_current_user_id, get_supabase
from app.core.rate_limit import limiter
from app.schemas.match_cards import (
    CreateMatchShareResponse,
    PublicMatchCard,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Match cards"])

# 16 urlsafe chars ~ 96 bits of entropy, plenty for a sharing token and short
# enough to look reasonable in a WhatsApp message preview.
_TOKEN_BYTES = 12


def _generate_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _share_url(token: str) -> str:
    base = (get_settings().app_url or "https://zedapply.com").rstrip("/")
    # Strip any /api or trailing path — app_url should be the public web origin.
    return f"{base}/m/{token}"


def _first_name(full_name: Any) -> str | None:
    if not full_name or not isinstance(full_name, str):
        return None
    parts = full_name.strip().split()
    return parts[0] if parts else None


@router.post(
    "/matches/{match_id}/share",
    response_model=CreateMatchShareResponse,
)
@limiter.limit("30/minute")
async def create_match_share(
    request: Request,
    match_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Create or reuse a public share token for one of the caller's matches."""
    del request  # required by limiter signature

    # Confirm the match belongs to this user. Avoid leaking match IDs across
    # accounts by returning 404 (not 403) for missing/foreign matches.
    own = (
        supabase.table("matches")
        .select("id")
        .eq("id", match_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not own.data:
        raise HTTPException(status_code=404, detail="Match not found")

    # Idempotency: one share row per (sender, match) per the UNIQUE constraint.
    existing = (
        supabase.table("match_shares")
        .select("token")
        .eq("match_id", match_id)
        .eq("sender_user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        token = existing.data[0]["token"]
        return CreateMatchShareResponse(
            token=token, share_url=_share_url(token), is_new=False
        )

    # Retry once on the rare token-collision case (96-bit entropy makes this
    # vanishingly rare, but a clean retry costs nothing and avoids a hard
    # error mode).
    last_exc: Exception | None = None
    for _ in range(2):
        token = _generate_token()
        try:
            ins = (
                supabase.table("match_shares")
                .insert(
                    {
                        "match_id": match_id,
                        "sender_user_id": user_id,
                        "token": token,
                    }
                )
                .execute()
            )
            if ins.data:
                return CreateMatchShareResponse(
                    token=token, share_url=_share_url(token), is_new=True
                )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue

    logger.exception(
        "match_share insert failed twice",
        extra={"user_id": user_id, "match_id": match_id},
    )
    raise HTTPException(
        status_code=500,
        detail="Could not create share link. Please try again.",
    ) from last_exc


@router.get(
    "/match-cards/{token}",
    response_model=PublicMatchCard,
)
@limiter.limit("120/minute")
async def get_match_card(
    request: Request,
    token: str,
    supabase=Depends(get_supabase),
):
    """Public, no-auth preview for a shared match."""
    del request  # limiter signature

    share = (
        supabase.table("match_shares")
        .select("match_id, sender_user_id")
        .eq("token", token)
        .limit(1)
        .execute()
    )
    if not share.data:
        raise HTTPException(status_code=404, detail="Share not found or expired")

    match_id = share.data[0]["match_id"]
    sender_user_id = share.data[0]["sender_user_id"]

    match = (
        supabase.table("matches")
        .select("score, matched_skills, created_at, jobs!inner(title, company, location)")
        .eq("id", match_id)
        .limit(1)
        .execute()
    )
    if not match.data:
        # Match was deleted after the share was created. Return 410 so the
        # frontend can show a "this match is no longer available" state.
        raise HTTPException(
            status_code=410, detail="This match is no longer available"
        )
    m = match.data[0]
    job = m.get("jobs") or {}
    if isinstance(job, list):
        job = job[0] if job else {}

    sender = (
        supabase.table("users")
        .select("full_name, referral_code")
        .eq("id", sender_user_id)
        .limit(1)
        .execute()
    )
    sender_row = sender.data[0] if sender.data else {}

    matched_raw = m.get("matched_skills") or []
    matched_skills = [str(s) for s in matched_raw if s]

    # Fire-and-forget view increment. Non-critical telemetry; never block the
    # response on it.
    try:
        supabase.rpc(
            "increment_match_share_views", {"p_token": token}
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.debug("increment_match_share_views failed: %s", exc)

    score_raw = m.get("score")
    try:
        score = max(0, min(100, int(round(float(score_raw or 0)))))
    except (TypeError, ValueError):
        score = 0

    return PublicMatchCard(
        title=str(job.get("title") or "Job match"),
        company=(job.get("company") or None) and str(job.get("company")),
        location=(job.get("location") or None) and str(job.get("location")),
        score=score,
        matched_skills_count=len(matched_skills),
        top_matched_skills=matched_skills[:3],
        sender_first_name=_first_name(sender_row.get("full_name")),
        sender_referral_code=sender_row.get("referral_code") or None,
        created_at=(
            str(m.get("created_at"))
            if m.get("created_at") is not None
            else None
        ),
    )
