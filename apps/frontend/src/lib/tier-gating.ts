/** Client-side tier gates — backend remains source of truth (tier_gating.py). */

import { FEATURE_TIER_MAP, tierAtLeast } from "@/lib/tier-features";

/** Score breakdowns, AI explanations, skill gaps — Starter and above. */
export function canViewMatchScoreBreakdown(tier: string | null | undefined): boolean {
  return tierAtLeast(tier, FEATURE_TIER_MAP.match_score_breakdown);
}

/** Tailored CV per match — Professional and Super Standard only (not Starter). */
export function canTailorCvForMatch(tier: string | null | undefined): boolean {
  return tierAtLeast(tier, FEATURE_TIER_MAP.tailor_cv);
}

export function canUseCoverLetterEditor(tier: string | null | undefined): boolean {
  return tierAtLeast(tier, FEATURE_TIER_MAP.cover_letter);
}
