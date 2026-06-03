/**
 * Canonical tier marketing copy — single source of truth for UI.
 * Aligns with backend `tier_gating.py` (free: 3/mo, welcome: 7/mo first month).
 */
import type { TierConfigRow } from "@/lib/api";
import { formatMatchesLimit, UNLIMITED_MATCHES } from "@/lib/tier-config";

export const FREE_TIER_MATCHES_DEFAULT = 3;
export const FREE_TIER_WELCOME_MATCHES = 7;
export const FREE_TIER_WELCOME_MONTHS = 1;

/** Full feature bullet for pricing cards */
export function freeTierMatchesFeatureLine(): string {
  return `${FREE_TIER_MATCHES_DEFAULT} job matches per month (${FREE_TIER_WELCOME_MATCHES}/mo welcome bonus for your first ${FREE_TIER_WELCOME_MONTHS} months)`;
}

/** Short homepage / plan blurb */
export function freeTierMatchesBlurb(): string {
  return `${FREE_TIER_MATCHES_DEFAULT} matches/mo (${FREE_TIER_WELCOME_MATCHES} welcome bonus first ${FREE_TIER_WELCOME_MONTHS} months)`;
}

/** Comparison table cell */
export function freeTierComparisonMatches(): string {
  return `${FREE_TIER_MATCHES_DEFAULT} (${FREE_TIER_WELCOME_MATCHES} welcome)`;
}

/** FAQ answer fragment */
export function freeTierFaqMatchExplanation(): string {
  return `Free includes ${FREE_TIER_WELCOME_MATCHES} matches per month for your first ${FREE_TIER_WELCOME_MONTHS} months, then ${FREE_TIER_MATCHES_DEFAULT} per month.`;
}

/** General “what is a match” FAQ can reference free limits */
export function tierMatchesFaqAnswer(): string {
  return `Each time our AI scores your CV against a job listing and delivers the result to you (via WhatsApp or dashboard), that counts as one match. ${freeTierFaqMatchExplanation()}`;
}

/** Comparison table cell for monthly match quotas (pricing page). */
export function tierMatchesComparisonCell(
  tier: "free" | "starter" | "professional" | "super_standard",
  tierRows: TierConfigRow[],
): string {
  if (tier === "free") {
    return freeTierComparisonMatches();
  }
  const row = tierRows.find((t) => t.tier === tier);
  if (!row) {
    const defaults: Record<string, string> = {
      starter: "50",
      professional: "125",
      super_standard: "Unlimited",
    };
    return defaults[tier];
  }
  if (row.matches_limit >= UNLIMITED_MATCHES) {
    return "Unlimited";
  }
  return formatMatchesLimit(row.matches_limit);
}

export interface TierComparisonFeature {
  name: string;
  free: string | boolean;
  starter: string | boolean;
  pro: string | boolean;
  super_standard: string | boolean;
}

const STATIC_COMPARISON_FEATURES: TierComparisonFeature[] = [
  { name: "WhatsApp alerts", free: true, starter: true, pro: true, super_standard: true },
  { name: "CV analysis", free: "Basic", starter: "Advanced", pro: "Advanced", super_standard: "Advanced" },
  { name: "Tailored CVs", free: false, starter: false, pro: true, super_standard: true },
  { name: "Cover letters", free: false, starter: false, pro: true, super_standard: true },
  { name: "Score breakdowns", free: false, starter: true, pro: true, super_standard: true },
  { name: "CV rewriting per role", free: false, starter: false, pro: true, super_standard: true },
  { name: "Priority support", free: false, starter: false, pro: true, super_standard: true },
  { name: "Interview prep notes", free: false, starter: false, pro: false, super_standard: true },
];

/** Feature comparison rows; match quotas follow live tier_config when rows are provided. */
export function buildTierComparisonFeatures(
  tierRows: TierConfigRow[] = [],
): TierComparisonFeature[] {
  return [
    {
      name: "Job matches / month",
      free: tierMatchesComparisonCell("free", tierRows),
      starter: tierMatchesComparisonCell("starter", tierRows),
      pro: tierMatchesComparisonCell("professional", tierRows),
      super_standard: tierMatchesComparisonCell("super_standard", tierRows),
    },
    ...STATIC_COMPARISON_FEATURES,
  ];
}

export const TIER_MARKETING_FEATURES: Record<string, string[]> = {
  free: [
    freeTierMatchesFeatureLine(),
    "WhatsApp alerts",
    "Basic CV analysis",
    "Job browsing",
  ],
  starter: [
    "50 job matches per month",
    "Advanced CV analysis",
    "Match score breakdowns",
    "Priority matching",
    "WhatsApp + web dashboard",
  ],
  professional: [
    "125 job matches per month",
    "AI cover letter generation",
    "Career coaching insights",
    "Priority support",
    "CV rewriting per role",
    "Everything in Starter",
  ],
  super_standard: [
    "Unlimited job matches",
    "Interview prep notes (Interview Call)",
    "Everything in Professional",
    "Priority delivery",
    "Concierge onboarding",
  ],
};

export function formatQuotaSummary(matchesUsed: number, matchesLimit: number): string {
  if (matchesLimit >= UNLIMITED_MATCHES) {
    return `${matchesUsed} matches delivered (unlimited plan)`;
  }
  return `${matchesUsed} / ${formatMatchesLimit(matchesLimit)} matches this period`;
}
