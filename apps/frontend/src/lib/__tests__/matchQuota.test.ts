import { describe, expect, it } from "vitest";
import { resolveMatchQuotaDisplay } from "@/lib/matchQuota";
import { UNLIMITED_MATCHES } from "@/lib/tier-config";

describe("resolveMatchQuotaDisplay", () => {
  it("shows starter tier as used/limit without summing unlimited sentinel", () => {
    const result = resolveMatchQuotaDisplay(
      {
        matches_used: 14,
        matches_limit: 50,
        matches_unlimited: false,
        remaining_quota: 36,
      },
      null,
    );
    expect(result.matchesUsed).toBe(14);
    expect(result.unlimited).toBe(false);
    expect(result.limitLabel).toBe("50");
    expect(result.usagePct).toBeCloseTo(28);
  });

  it("treats 99999 limit as unlimited even when used+remaining would mislead", () => {
    const result = resolveMatchQuotaDisplay(
      {
        matches_used: 14,
        remaining_quota: UNLIMITED_MATCHES - 14,
      },
      { matches_limit: UNLIMITED_MATCHES, matches_unlimited: true },
    );
    expect(result.unlimited).toBe(true);
    expect(result.limitLabel).toBe("Unlimited");
  });

  it("prefers API matches_used over credited_count", () => {
    const result = resolveMatchQuotaDisplay(
      { matches_used: 5, credited_count: 99, matches_limit: 50 },
      null,
    );
    expect(result.matchesUsed).toBe(5);
  });
});
