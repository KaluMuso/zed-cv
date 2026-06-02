/**
 * Canonical tier marketing copy — single source of truth for UI.
 * Aligns with backend `tier_gating.py` (free: 3/mo, welcome: 7/mo first month).
 */
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
