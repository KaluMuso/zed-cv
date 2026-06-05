import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MatchExplanationModal } from "@/app/matches/_components/MatchExplanationModal";
import type { MatchData } from "@/lib/api";

const MATCH: MatchData = {
  id: "m1",
  created_at: "2026-05-18T00:00:00Z",
  score: 72,
  vector_score: 38,
  skill_score: 12,
  bonus_score: 5,
  semantic_score: 38,
  skills_score: 12,
  experience_score: 10,
  location_score: 8,
  recency_score: 4,
  matched_skills: ["python", "sql"],
  missing_skills: ["kubernetes", "terraform"],
  explanation:
    "Semantic fit 38/50; required skills 12/20. Preferences match: remote arrangement, salary range overlap.",
  job: {
    id: "j1",
    title: "Backend Engineer",
    company: "ACME",
    location: "Lusaka",
    closing_date: null,
  },
};

describe("MatchExplanationModal", () => {
  it("renders solid panel, preferences note, and skill gap callout for starter+", () => {
    const onClose = vi.fn();
    render(
      <MatchExplanationModal
        match={MATCH}
        open
        onClose={onClose}
        subscriptionTier="starter"
      />,
    );

    const backdrop = document.body.querySelector(".modal-backdrop");
    expect(backdrop).toBeTruthy();

    expect(screen.getByRole("dialog")).toHaveClass("modal-panel");
    expect(screen.getByText("Preferences match")).toBeInTheDocument();
    expect(screen.getByText(/remote arrangement, salary range overlap/)).toBeInTheDocument();
    expect(screen.getByText("Matched skills")).toBeInTheDocument();
    expect(screen.getByText("Skills to develop")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("kubernetes")).toBeInTheDocument();
    expect(screen.getByText("terraform")).toBeInTheDocument();
  });

  it("shows only score and upgrade prompt on free tier", () => {
    render(
      <MatchExplanationModal
        match={MATCH}
        open
        onClose={vi.fn()}
        subscriptionTier="free"
      />,
    );

    expect(screen.getByText("Your overall match score")).toBeInTheDocument();
    expect(screen.getByTestId("match-breakdown-upgrade")).toBeInTheDocument();
    expect(screen.getByText(/Starter plan and above/i)).toBeInTheDocument();
    expect(screen.getByText(/Your Free plan shows only the overall match score/i)).toBeInTheDocument();
    expect(screen.queryByText("Score breakdown")).not.toBeInTheDocument();
    expect(screen.queryByText("AI explanation")).not.toBeInTheDocument();
    expect(screen.queryByText("Matched skills")).not.toBeInTheDocument();
  });

  it("omits skill breakdown when both lists are empty", () => {
    render(
      <MatchExplanationModal
        match={{ ...MATCH, matched_skills: [], missing_skills: [] }}
        open
        onClose={vi.fn()}
        subscriptionTier="professional"
      />,
    );
    expect(screen.queryByTestId("match-skills-breakdown")).not.toBeInTheDocument();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <MatchExplanationModal
        match={MATCH}
        open
        onClose={onClose}
        subscriptionTier="starter"
      />,
    );

    const backdrop = document.body.querySelector(".modal-backdrop");
    expect(backdrop).toBeTruthy();
    await user.click(backdrop!);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
