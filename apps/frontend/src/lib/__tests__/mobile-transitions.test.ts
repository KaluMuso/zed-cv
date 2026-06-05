import { describe, expect, it } from "vitest";
import { getRouteTransitionVariant } from "@/lib/mobile-transitions";

describe("getRouteTransitionVariant", () => {
  it("slides right when moving forward across tabs", () => {
    expect(getRouteTransitionVariant("/jobs", "/matches")).toBe("tab-right");
    expect(getRouteTransitionVariant("/matches", "/applications")).toBe("tab-right");
  });

  it("slides left when moving backward across tabs", () => {
    expect(getRouteTransitionVariant("/applications", "/matches")).toBe("tab-left");
    expect(getRouteTransitionVariant("/profile", "/jobs")).toBe("tab-left");
  });

  it("fades for non-tab navigation", () => {
    expect(getRouteTransitionVariant("/jobs", "/jobs/abc")).toBe("fade");
    expect(getRouteTransitionVariant("/dashboard", "/settings/account")).toBe("fade");
  });
});
