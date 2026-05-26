import { describe, expect, it } from "vitest";
import { splitMatchExplanation } from "../matchExplanationDisplay";

describe("splitMatchExplanation", () => {
  it("returns nulls for empty input", () => {
    expect(splitMatchExplanation(null)).toEqual({
      main: null,
      preferencesNote: null,
    });
  });

  it("keeps full text when no preferences line", () => {
    expect(
      splitMatchExplanation("Semantic fit 40/50; required skills 16/20."),
    ).toEqual({
      main: "Semantic fit 40/50; required skills 16/20.",
      preferencesNote: null,
    });
  });

  it("splits appended preferences note", () => {
    expect(
      splitMatchExplanation(
        "Semantic fit 40/50. Preferences match: remote arrangement, salary range overlap.",
      ),
    ).toEqual({
      main: "Semantic fit 40/50.",
      preferencesNote: "Preferences match: remote arrangement, salary range overlap.",
    });
  });
});
