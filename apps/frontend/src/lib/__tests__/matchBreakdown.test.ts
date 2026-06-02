import { describe, expect, it } from "vitest";
import {
  countRequiredJobSkills,
  formatBreakdownFraction,
  formatRequiredSkillsDetail,
  matchBreakdownRows,
} from "../matchBreakdown";

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
    expect(formatBreakdownFraction(rows[0].value, rows[0].max)).toBe("40/50 pts");
  });

  it("labels skills row with required-skill counts", () => {
    const rows = matchBreakdownRows({
      skills_score: 20,
      matched_skills: ["planning", "project management"],
      missing_skills: [],
    });
    const skills = rows.find((r) => r.key === "skills");
    expect(skills?.label).toBe("Required skills");
    expect(skills?.detail).toBe("2/2 required skills");
    expect(countRequiredJobSkills({ matched_skills: ["a"], missing_skills: ["b"] })).toEqual({
      matched: 1,
      total: 2,
    });
    expect(formatRequiredSkillsDetail({ matched: 2, total: 2 })).toBe("2/2 required skills");
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
