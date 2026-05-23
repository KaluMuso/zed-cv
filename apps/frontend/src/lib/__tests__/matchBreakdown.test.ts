import { describe, expect, it } from "vitest";
import { formatBreakdownFraction, matchBreakdownRows } from "../matchBreakdown";

describe("matchBreakdownRows", () => {
  it("returns five v2 components with correct caps", () => {
    const rows = matchBreakdownRows({
      semantic_score: 40,
      skills_score: 16,
      experience_score: 12,
      location_score: 10,
      recency_score: 4,
    });
    expect(rows).toHaveLength(5);
    expect(rows.map((r) => r.max)).toEqual([50, 20, 15, 10, 5]);
    expect(formatBreakdownFraction(rows[0].value, rows[0].max)).toBe("40/50");
  });

  it("falls back to legacy vector/skill/bonus fields", () => {
    const rows = matchBreakdownRows({
      vector_score: 35,
      skill_score: 10,
      bonus_score: 12,
    });
    expect(rows[0].value).toBe(35);
    expect(rows[3].value).toBe(12);
  });
});
