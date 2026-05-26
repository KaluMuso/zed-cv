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
  it("renders solid panel, preferences note, and skill gap callout", () => {
    const onClose = vi.fn();
    render(<MatchExplanationModal match={MATCH} open onClose={onClose} />);

    const backdrop = document.body.querySelector(".modal-backdrop");
    expect(backdrop).toBeTruthy();

    expect(screen.getByRole("dialog")).toHaveClass("modal-panel");
    expect(screen.getByText("Preferences match")).toBeInTheDocument();
    expect(screen.getByText(/remote arrangement, salary range overlap/)).toBeInTheDocument();
    expect(screen.getByText("Skill gap")).toBeInTheDocument();
    expect(screen.getByText("kubernetes")).toBeInTheDocument();
    expect(screen.getByText("terraform")).toBeInTheDocument();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<MatchExplanationModal match={MATCH} open onClose={onClose} />);

    const backdrop = document.body.querySelector(".modal-backdrop");
    expect(backdrop).toBeTruthy();
    await user.click(backdrop!);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
