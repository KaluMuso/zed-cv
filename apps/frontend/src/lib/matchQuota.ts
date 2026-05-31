import { UNLIMITED_MATCHES, formatMatchesLimit } from "@/lib/tier-config";

export type MatchQuotaSource = {
  matches_used?: number;
  credited_count?: number;
  matches_limit?: number;
  matches_unlimited?: boolean;
  remaining_quota?: number;
};

export type SubscriptionQuotaSource = {
  matches_used?: number;
  matches_limit?: number;
  matches_unlimited?: boolean;
};

/** Resolve used/limit for the matches page quota card. Never sums used+remaining when unlimited. */
export function resolveMatchQuotaDisplay(
  data: MatchQuotaSource | null | undefined,
  sub: SubscriptionQuotaSource | null | undefined,
): {
  matchesUsed: number;
  matchesLimit: number;
  unlimited: boolean;
  limitLabel: string;
  usagePct: number;
} {
  const matchesUsed =
    data?.matches_used ??
    data?.credited_count ??
    sub?.matches_used ??
    (data?.remaining_quota != null
      ? Math.max(0, (sub?.matches_limit ?? 50) - data.remaining_quota)
      : 0);

  const rawLimit =
    data?.matches_limit ??
    sub?.matches_limit ??
    (data?.remaining_quota != null && matchesUsed >= 0
      ? matchesUsed + data.remaining_quota
      : 50);

  const unlimited =
    Boolean(data?.matches_unlimited ?? sub?.matches_unlimited) ||
    rawLimit >= UNLIMITED_MATCHES;

  const matchesLimit = unlimited ? UNLIMITED_MATCHES : rawLimit;
  const limitLabel = formatMatchesLimit(matchesLimit);
  const usagePct =
    unlimited || matchesLimit <= 0
      ? matchesUsed > 0
        ? 8
        : 0
      : Math.min(100, (matchesUsed / matchesLimit) * 100);

  return {
    matchesUsed,
    matchesLimit,
    unlimited,
    limitLabel,
    usagePct,
  };
}
