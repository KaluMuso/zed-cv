import { describe, it, expect, beforeEach } from "vitest";
import { useTailoredCvBuilderStore, DEFAULT_DRAFT } from "../store";

describe("useTailoredCvBuilderStore", () => {
  beforeEach(() => {
    useTailoredCvBuilderStore.getState().resetDraft();
  });

  it("updates basics fields for live preview sync", () => {
    useTailoredCvBuilderStore.getState().updateBasics({ fullName: "Test User" });
    expect(useTailoredCvBuilderStore.getState().draft.basics.fullName).toBe("Test User");
    expect(useTailoredCvBuilderStore.getState().draft.experience).toEqual(DEFAULT_DRAFT.experience);
  });

  it("advances wizard step", () => {
    useTailoredCvBuilderStore.getState().setStep("experience");
    expect(useTailoredCvBuilderStore.getState().step).toBe("experience");
  });
});
