import { describe, expect, it } from "vitest";
import { formatTierLabel, getNextUpgradeTier } from "@/lib/tier-display";

describe("getNextUpgradeTier", () => {
  it("steps through paid tiers", () => {
    expect(getNextUpgradeTier("free")).toBe("starter");
    expect(getNextUpgradeTier("starter")).toBe("professional");
    expect(getNextUpgradeTier("professional")).toBe("super_standard");
    expect(getNextUpgradeTier("super_standard")).toBeNull();
  });

  it("formats labels for upgrade banner", () => {
    expect(formatTierLabel("professional")).toBe("Professional");
  });
});
