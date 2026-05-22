import { describe, it, expect } from "vitest";
import { formatDashboardHeaderDate } from "./format-dashboard-date";

describe("formatDashboardHeaderDate", () => {
  it("formats as uppercase weekday, day, month, year", () => {
    const result = formatDashboardHeaderDate(new Date(2026, 4, 22));
    expect(result).toBe("FRIDAY, 22 MAY 2026");
  });
});
