import { describe, expect, it } from "vitest";
import {
  FREE_TIER_MATCHES_DEFAULT,
  FREE_TIER_WELCOME_MATCHES,
  TIER_MARKETING_FEATURES,
  buildTierComparisonFeatures,
  freeTierMatchesBlurb,
  freeTierMatchesFeatureLine,
  tierMatchesComparisonCell,
  tierMatchesFaqAnswer,
} from "../tier-marketing";

describe("tier-marketing", () => {
  it("uses backend-aligned free tier limits", () => {
    expect(FREE_TIER_MATCHES_DEFAULT).toBe(3);
    expect(FREE_TIER_WELCOME_MATCHES).toBe(7);
  });

  it("consistent copy across surfaces", () => {
    expect(freeTierMatchesFeatureLine()).toContain("3 job matches");
    expect(freeTierMatchesFeatureLine()).toContain("7");
    expect(freeTierMatchesBlurb()).toContain("3 matches");
    expect(tierMatchesFaqAnswer()).toContain("3 per month");
  });

  it("starter does not claim tailored CVs (professional+ only)", () => {
    const starter = TIER_MARKETING_FEATURES.starter.join(" ").toLowerCase();
    expect(starter).not.toContain("tailored cv");
    expect(starter).toContain("score breakdown");
  });

  it("professional includes cover letters and tailored CV features", () => {
    const pro = TIER_MARKETING_FEATURES.professional.join(" ").toLowerCase();
    expect(pro).toContain("cover letter");
    expect(pro).toContain("cv rewriting");
  });

  it("comparison table reflects tier_config match limits", () => {
    const rows = [
      { tier: "starter", display_name: "Starter", price_ngwee: 12500, matches_limit: 60, sort_order: 1 },
      { tier: "professional", display_name: "Pro", price_ngwee: 25000, matches_limit: 130, sort_order: 2 },
      { tier: "super_standard", display_name: "Super", price_ngwee: 50000, matches_limit: 99999, sort_order: 3 },
    ];
    expect(tierMatchesComparisonCell("starter", rows)).toBe("60");
    expect(tierMatchesComparisonCell("professional", rows)).toBe("130");
    expect(tierMatchesComparisonCell("super_standard", rows)).toBe("Unlimited");
    const table = buildTierComparisonFeatures(rows);
    expect(table[0]?.starter).toBe("60");
    expect(table[0]?.pro).toBe("130");
  });
});
