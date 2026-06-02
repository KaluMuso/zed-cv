import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MatchCard } from "../MatchCard";

vi.mock("@/hooks/useUserTier", () => ({
  useUserTier: () => ({ tier: "professional", loading: false }),
}));

vi.mock("@/components/share/JobShareButtons", () => ({
  JobShareButtons: () => null,
}));
import type { MatchData } from "@/lib/api";

const baseMatch: MatchData = {
  id: "m1",
  score: 72,
  vector_score: 40,
  skill_score: 20,
  bonus_score: 12,
  matched_skills: ["excel"],
  missing_skills: [],
  explanation: null,
  created_at: "2026-05-18T00:00:00Z",
  job: {
    id: "j1",
    title: "Accountant",
    company: "Acme",
    location: "Lusaka",
    closing_date: new Date(Date.now() - 86400000).toISOString().slice(0, 10),
    quality_score: 80,
    skills: [],
    description: "Role description",
    is_active: true,
    visibility_status: "recently_closed",
  },
};

describe("MatchCard closed UX", () => {
  it("renders greyed CLOSED badge and disabled apply", () => {
    render(<MatchCard match={baseMatch} expired={false} />);
    expect(screen.getByTestId("match-closed-badge")).toHaveTextContent("CLOSED");
    expect(screen.getByTestId("match-apply-closed")).toBeDisabled();
    const card = screen.getByTestId("match-card");
    expect(card).toHaveStyle({ opacity: "0.6" });
  });
});
