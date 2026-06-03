import { formatMatchesLimit, UNLIMITED_MATCHES } from "@/lib/tier-config";

/** Short tier label for nav and cards. */
export const TIER_NAV_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  super_standard: "Super Standard",
};

const TIER_UPGRADE_ORDER = [
  "free",
  "starter",
  "professional",
  "super_standard",
] as const;

/** Next paid tier for upgrade CTAs; null when already on top tier. */
export function getNextUpgradeTier(tier: string): string | null {
  const idx = TIER_UPGRADE_ORDER.indexOf(tier as (typeof TIER_UPGRADE_ORDER)[number]);
  if (idx < 0 || idx >= TIER_UPGRADE_ORDER.length - 1) return null;
  return TIER_UPGRADE_ORDER[idx + 1];
}

export function formatTierLabel(tier: string): string {
  return TIER_NAV_LABELS[tier] ?? tier.replace(/_/g, " ");
}

export function formatTierNavSubtitle(
  tier: string,
  matchesUsed?: number,
  matchesLimit?: number,
): string {
  const label = TIER_NAV_LABELS[tier] ?? tier.replace(/_/g, " ");
  if (matchesLimit === undefined) {
    return label;
  }
  const limitLabel =
    matchesLimit >= UNLIMITED_MATCHES
      ? "unlimited matches"
      : `${formatMatchesLimit(matchesLimit)} matches`;
  if (matchesUsed !== undefined && matchesLimit < UNLIMITED_MATCHES) {
    return `${label} · ${matchesUsed} of ${formatMatchesLimit(matchesLimit)} matches`;
  }
  return `${label} · ${limitLabel}`;
}
