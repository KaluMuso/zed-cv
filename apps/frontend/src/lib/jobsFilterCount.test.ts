import { describe, expect, it } from "vitest";
import { countActiveJobFilters } from "./jobsFilterCount";

const defaults = {
  searchQuery: "",
  searchInput: "",
  location: "",
  sort: "recent" as const,
  selectedSkills: [] as string[],
  employmentType: "",
  workArrangement: "",
  showClosed: false,
  listPreset: "all" as const,
};

describe("countActiveJobFilters", () => {
  it("returns 0 when all filters are default", () => {
    expect(countActiveJobFilters(defaults)).toBe(0);
  });

  it("counts saved preset and location independently", () => {
    expect(
      countActiveJobFilters({
        ...defaults,
        listPreset: "saved",
        location: "Lusaka",
      }),
    ).toBe(2);
  });

  it("counts search, skills, and show closed", () => {
    expect(
      countActiveJobFilters({
        ...defaults,
        searchQuery: "accountant",
        selectedSkills: ["finance"],
        showClosed: true,
      }),
    ).toBe(3);
  });

  it("does not double-count sort when closing preset is active", () => {
    expect(
      countActiveJobFilters({
        ...defaults,
        listPreset: "closing",
        sort: "closing",
      }),
    ).toBe(1);
  });
});
