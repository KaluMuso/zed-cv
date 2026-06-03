import { describe, expect, it } from "vitest";
import { buildDashboardMatchStats } from "@/lib/dashboard-stats";
import type { MatchData } from "@/lib/api";
import { UNLIMITED_MATCHES } from "@/lib/tier-config";

const match = (score: number): MatchData =>
  ({
    id: `m-${score}`,
    score,
    job: { id: `j-${score}`, title: "Role", company: "Co" },
    matched_skills: [],
    missing_skills: [],
  }) as MatchData;

describe("buildDashboardMatchStats", () => {
  it("uses full match list length for pool count (not API default cap)", () => {
    const matches = Array.from({ length: 15 }, (_, i) => match(80 - i));
    const result = buildDashboardMatchStats(
      matches,
      { matches, matches_limit: 50, matches_used: 15, remaining_quota: 35 },
      null,
    );
    expect(result.poolCount).toBe(15);
    expect(result.topMatches).toHaveLength(3);
    expect(result.topMatches[0]?.score).toBe(80);
  });

  it("resolves unlimited quota from remaining when subscription shows 0 used", () => {
    const matches = Array.from({ length: 10 }, () => match(75));
    const result = buildDashboardMatchStats(
      matches,
      {
        matches,
        remaining_quota: UNLIMITED_MATCHES - 10,
        matches_limit: UNLIMITED_MATCHES,
        matches_unlimited: true,
      },
      {
        tier: "super_standard",
        matches_used: 0,
        matches_limit: UNLIMITED_MATCHES,
        matches_unlimited: true,
        remaining_quota: UNLIMITED_MATCHES,
      },
    );
    expect(result.quota.matchesUsed).toBe(10);
    expect(result.quota.unlimited).toBe(true);
    expect(result.poolCount).toBe(10);
  });
});
