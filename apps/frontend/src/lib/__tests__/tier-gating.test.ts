import { describe, expect, it } from "vitest";
import { canTailorCvForMatch } from "../tier-gating";

describe("canTailorCvForMatch", () => {
  it("allows professional and super_standard", () => {
    expect(canTailorCvForMatch("professional")).toBe(true);
    expect(canTailorCvForMatch("super_standard")).toBe(true);
  });

  it("blocks free and starter", () => {
    expect(canTailorCvForMatch("free")).toBe(false);
    expect(canTailorCvForMatch("starter")).toBe(false);
    expect(canTailorCvForMatch(null)).toBe(false);
  });
});
