import { describe, expect, it } from "vitest";
import { computeJobVisibilityStatus, isClosedForMatchesFeed } from "@/lib/jobVisibility";

describe("isClosedForMatchesFeed", () => {
  it("treats recently_closed and archived as closed", () => {
    expect(
      isClosedForMatchesFeed({
        is_active: true,
        closing_date: null,
        visibility_status: "recently_closed",
      }),
    ).toBe(true);
    expect(
      isClosedForMatchesFeed({
        is_active: false,
        closing_date: null,
        visibility_status: "archived",
      }),
    ).toBe(true);
    expect(
      isClosedForMatchesFeed({
        is_active: true,
        closing_date: null,
        visibility_status: "open",
      }),
    ).toBe(false);
  });

  it("matches computeJobVisibilityStatus for derived states", () => {
    const ref = new Date("2026-06-03T12:00:00Z");
    const job = {
      is_active: true,
      closing_date: "2026-05-01",
      visibility_status: undefined as undefined,
    };
    const status = computeJobVisibilityStatus(job, ref);
    expect(status === "recently_closed" || status === "archived").toBe(true);
    expect(isClosedForMatchesFeed(job)).toBe(true);
  });
});
