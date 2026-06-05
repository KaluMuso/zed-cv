import { describe, expect, it } from "vitest";
import {
  canTailorCvForMatch,
  canUseCoverLetterEditor,
  canViewMatchScoreBreakdown,
} from "../tier-gating";

describe("canViewMatchScoreBreakdown", () => {
  it("allows starter and above", () => {
    expect(canViewMatchScoreBreakdown("starter")).toBe(true);
    expect(canViewMatchScoreBreakdown("professional")).toBe(true);
    expect(canViewMatchScoreBreakdown("super_standard")).toBe(true);
  });

  it("blocks free and unknown tiers", () => {
    expect(canViewMatchScoreBreakdown("free")).toBe(false);
    expect(canViewMatchScoreBreakdown(null)).toBe(false);
    expect(canViewMatchScoreBreakdown(undefined)).toBe(false);
  });
});

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

describe("canUseCoverLetterEditor", () => {
  it("matches tailored CV tier gate", () => {
    expect(canUseCoverLetterEditor("professional")).toBe(true);
    expect(canUseCoverLetterEditor("free")).toBe(false);
  });
});
