import { describe, expect, it } from "vitest";
import { buildCompletenessSavePatch } from "../buildCompletenessSavePatch";
import type { JobPreferences } from "@/lib/api";

function basePrefs(): JobPreferences {
  return {
    target_roles: [],
    target_roles_source: "user_provided",
    salary_min: 500000,
    salary_max: 800000,
    salary_currency: "ZMW",
    salary_frequency: "monthly",
    preferred_work_arrangement: "hybrid",
    willing_to_relocate: true,
    acceptable_regions: ["Lusaka"],
    languages: [],
    industries: [],
    extras: { education_level: "Bachelor's degree", notice_period: "1 month" },
    auto_populated_at: null,
    manually_updated_at: null,
    auto_populated_fields: [],
  };
}

describe("buildCompletenessSavePatch", () => {
  it("builds profile patch for full name", () => {
    const result = buildCompletenessSavePatch("full_name", null, {
      fullName: "Jane Doe",
      email: "",
      yearsExperience: 0,
    });
    expect(result).toEqual({ kind: "profile", patch: { full_name: "Jane Doe" } });
  });

  it("rejects inverted salary range", () => {
    const prefs = basePrefs();
    prefs.salary_min = 900000;
    prefs.salary_max = 100000;
    const result = buildCompletenessSavePatch("target_salary", prefs, {
      fullName: "",
      email: "",
      yearsExperience: 0,
    });
    expect(result).toEqual({
      kind: "invalid",
      salaryError: "Minimum can't be more than maximum.",
    });
  });

  it("builds extras patch for education level", () => {
    const result = buildCompletenessSavePatch("education_level", basePrefs(), {
      fullName: "",
      email: "",
      yearsExperience: 0,
    });
    expect(result).toEqual({
      kind: "preferences",
      patch: { extras: { education_level: "Bachelor's degree", notice_period: "1 month" } },
    });
  });
});
