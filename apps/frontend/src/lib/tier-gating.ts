/** Client-side tier gates — backend remains source of truth. */

const MATCH_TAILORED_CV_TIERS = new Set(["professional", "super_standard"]);

export function canTailorCvForMatch(tier: string | null | undefined): boolean {
  return MATCH_TAILORED_CV_TIERS.has(tier ?? "free");
}
