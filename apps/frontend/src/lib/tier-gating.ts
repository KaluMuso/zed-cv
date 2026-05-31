/** Client-side tier gates — backend remains source of truth (tier_gating.py). */

/** Tailored CV per match — Professional and Super Standard only (not Starter). */
const MATCH_TAILORED_CV_TIERS = new Set(["professional", "super_standard"]);
const COVER_LETTER_EDITOR_TIERS = new Set(["professional", "super_standard"]);

export function canTailorCvForMatch(tier: string | null | undefined): boolean {
  return MATCH_TAILORED_CV_TIERS.has(tier ?? "free");
}

export function canUseCoverLetterEditor(tier: string | null | undefined): boolean {
  return COVER_LETTER_EDITOR_TIERS.has(tier ?? "free");
}
