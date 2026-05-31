"""Canonical tier marketing copy — must match app/core/tier_gating.py gates."""
from __future__ import annotations

# Feature gates (tier_gating.py): tailored CV + cover letter = professional+;
# interview prep = super_standard only.
TIER_WHATSAPP_BLURB: dict[str, str] = {
    "free": "CV upload + WhatsApp digest",
    "starter": "advanced CV analysis + score breakdowns",
    "professional": "cover letters + tailored CVs per match",
    "super_standard": "unlimited matches + Bwana Interview prep",
}
