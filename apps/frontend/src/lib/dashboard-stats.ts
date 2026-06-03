import type { MatchData, MatchListResponse, Subscription } from "@/lib/api";
import { resolveMatchQuotaDisplay } from "@/lib/matchQuota";

/** GET /matches defaults to 10; API max is 50 — load full delivered set for dashboard. */
export const DASHBOARD_MATCHES_FETCH_LIMIT = 50;

export type DashboardQuotaDisplay = ReturnType<typeof resolveMatchQuotaDisplay>;

export function buildDashboardMatchStats(
  matches: MatchData[],
  matchList: MatchListResponse,
  subscription: Subscription | null,
): {
  topMatches: MatchData[];
  poolCount: number;
  avgScore: number | null;
  quota: DashboardQuotaDisplay;
} {
  const quota = resolveMatchQuotaDisplay(matchList, subscription);
  const sorted = [...matches].sort((a, b) => b.score - a.score);
  const poolCount = Math.max(sorted.length, quota.matchesUsed);
  const avgScore =
    sorted.length > 0
      ? Math.round(sorted.reduce((sum, m) => sum + m.score, 0) / sorted.length)
      : null;

  return {
    topMatches: sorted.slice(0, 3),
    poolCount,
    avgScore,
    quota,
  };
}
