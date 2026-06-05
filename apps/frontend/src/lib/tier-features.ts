/**
 * Feature → minimum tier. Mirrors apps/backend/app/core/tier_gating.py.
 */

export type SubscriptionTier =
  | "free"
  | "starter"
  | "professional"
  | "super_standard";

export type TierFeature =
  | "match_score_breakdown"
  | "tailor_cv"
  | "cover_letter"
  | "unlock_prep"
  | "bulk_apply"
  | "whatsapp_priority_digest"
  | "api_access";

const TIER_ORDER: SubscriptionTier[] = [
  "free",
  "starter",
  "professional",
  "super_standard",
];

export const FEATURE_TIER_MAP: Record<TierFeature, SubscriptionTier> = {
  match_score_breakdown: "starter",
  tailor_cv: "professional",
  cover_letter: "professional",
  unlock_prep: "super_standard",
  bulk_apply: "professional",
  whatsapp_priority_digest: "super_standard",
  api_access: "super_standard",
};

export const FEATURE_LABELS: Record<TierFeature, string> = {
  match_score_breakdown: "Match score breakdown",
  tailor_cv: "Tailored CV per match",
  cover_letter: "AI cover letter",
  unlock_prep: "Interview prep",
  bulk_apply: "Bulk apply",
  whatsapp_priority_digest: "Priority WhatsApp digest",
  api_access: "API access",
};

export function normalizeTier(raw: string | null | undefined): SubscriptionTier {
  const key = (raw ?? "free").trim().toLowerCase();
  if (key === "starter" || key === "professional" || key === "super_standard") {
    return key;
  }
  return "free";
}

export function tierAtLeast(
  userTier: string | null | undefined,
  requiredTier: SubscriptionTier,
): boolean {
  const user = normalizeTier(userTier);
  return TIER_ORDER.indexOf(user) >= TIER_ORDER.indexOf(requiredTier);
}

export function tierDisplayName(tier: SubscriptionTier): string {
  const names: Record<SubscriptionTier, string> = {
    free: "Free",
    starter: "Starter",
    professional: "Professional",
    super_standard: "Super Standard",
  };
  return names[tier];
}

/** Kwacha/month list prices (ngwee in tier-config API). */
export const TIER_PRICE_KWACHA: Record<SubscriptionTier, number> = {
  free: 0,
  starter: 125,
  professional: 250,
  super_standard: 500,
};
