import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TierGate } from "../TierGate";

vi.mock("@/hooks/useUserTier", () => ({
  useUserTier: vi.fn(),
}));

import { useUserTier } from "@/hooks/useUserTier";

const features = [
  "tailor_cv",
  "cover_letter",
  "unlock_prep",
  "bulk_apply",
  "whatsapp_priority_digest",
  "api_access",
] as const;

describe("TierGate", () => {
  it.each(features)("renders upgrade CTA for free user (%s)", (feature) => {
    vi.mocked(useUserTier).mockReturnValue({ tier: "free", loading: false });
    render(
      <TierGate feature={feature}>
        <button type="button">Feature action</button>
      </TierGate>,
    );
    expect(screen.getByTestId(`upgrade-${feature}`)).toBeInTheDocument();
    expect(screen.queryByText("Feature action")).not.toBeInTheDocument();
  });

  it("renders children for professional tailor_cv", () => {
    vi.mocked(useUserTier).mockReturnValue({ tier: "professional", loading: false });
    render(
      <TierGate feature="tailor_cv">
        <button type="button">Tailor</button>
      </TierGate>,
    );
    expect(screen.getByText("Tailor")).toBeInTheDocument();
  });

  it("renders children for super_standard unlock_prep", () => {
    vi.mocked(useUserTier).mockReturnValue({ tier: "super_standard", loading: false });
    render(
      <TierGate feature="unlock_prep">
        <button type="button">Prep</button>
      </TierGate>,
    );
    expect(screen.getByText("Prep")).toBeInTheDocument();
  });
});
