import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobDetailMatchPanel } from "@/components/jobs/JobDetailMatchPanel";
import type { MatchData } from "@/lib/api";

const MATCH: MatchData = {
  id: "m1",
  created_at: "2026-05-18T00:00:00Z",
  score: 64,
  vector_score: 31,
  skill_score: 5,
  bonus_score: 0,
  semantic_score: 31,
  skills_score: 5,
  experience_score: 15,
  location_score: 10,
  recency_score: 2,
  matched_skills: ["excel"],
  missing_skills: ["sales"],
  explanation: "Semantic 31/50, skills 5/20.",
  job: {
    id: "j1",
    title: "Sales Intern",
    company: "Evimeria",
    location: "Lusaka",
    closing_date: null,
  },
};

describe("JobDetailMatchPanel", () => {
  it("shows score only and upgrade prompt on free tier", () => {
    render(
      <JobDetailMatchPanel
        match={MATCH}
        signedIn
        viewerName="Kaluba"
        subscriptionTier="free"
      />,
    );

    expect(screen.getByText("Why you're a good match")).toBeInTheDocument();
    expect(screen.getByTestId("match-breakdown-upgrade")).toBeInTheDocument();
    expect(screen.queryByText("Score breakdown")).not.toBeInTheDocument();
    expect(screen.queryByText("Skills overlap")).not.toBeInTheDocument();
  });

  it("shows full breakdown for starter tier", () => {
    render(
      <JobDetailMatchPanel
        match={MATCH}
        signedIn
        viewerName="Kaluba"
        subscriptionTier="starter"
      />,
    );

    expect(screen.getByText("Score breakdown")).toBeInTheDocument();
    expect(screen.getAllByText("Skills overlap").length).toBeGreaterThan(0);
    expect(screen.queryByTestId("match-breakdown-upgrade")).not.toBeInTheDocument();
  });
});
