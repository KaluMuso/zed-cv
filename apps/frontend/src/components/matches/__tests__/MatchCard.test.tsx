import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MatchCard } from "../MatchCard";
import type { MatchData } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("@/components/shared/TierGate", () => ({
  TierGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/share/JobShareButtons", () => ({
  JobShareButtons: () => <span data-testid="job-share-stub" />,
}));

const baseMatch: MatchData = {
  id: "m1",
  score: 88,
  vector_score: 82,
  skill_score: 91,
  bonus_score: 5,
  matched_skills: ["python"],
  missing_skills: [],
  explanation: null,
  created_at: "2026-05-18T00:00:00Z",
  job: {
    id: "j1",
    title: "Software Engineer",
    company: "ACME Zambia",
    location: "Lusaka",
    closing_date: null,
    quality_score: 80,
    skills: [],
    description: "Build APIs",
    apply_url: "https://careers.example.com/apply",
    apply_email: null,
    source_url: null,
  },
};

describe("MatchCard", () => {
  it("renders the match score", () => {
    render(<MatchCard match={baseMatch} onApplyClick={vi.fn()} />);
    expect(screen.getByText("88")).toBeInTheDocument();
    expect(screen.getByText("Software Engineer")).toBeInTheDocument();
  });

  it("shows an active Apply button that calls onApplyClick", async () => {
    const user = userEvent.setup();
    const onApplyClick = vi.fn();
    const match: MatchData = {
      ...baseMatch,
      job: { ...baseMatch.job, apply_url: null, apply_email: "hr@acme.zm" },
    };
    render(<MatchCard match={match} onApplyClick={onApplyClick} />);
    const btn = screen.getByTestId("match-apply-active");
    expect(btn).toBeEnabled();
    await user.click(btn);
    expect(onApplyClick).toHaveBeenCalledTimes(1);
  });

  it("disables apply when expired/archived", () => {
    render(<MatchCard match={baseMatch} expired onApplyClick={vi.fn()} />);
    expect(screen.getByTestId("match-apply-closed")).toBeDisabled();
    expect(screen.getByText("EXPIRED")).toBeInTheDocument();
  });

  it("shows CLOSED badge for recently closed jobs", () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const match: MatchData = {
      ...baseMatch,
      job: {
        ...baseMatch.job,
        closing_date: yesterday.toISOString().slice(0, 10),
        visibility_status: "recently_closed",
      },
    };
    render(<MatchCard match={match} onApplyClick={vi.fn()} />);
    expect(screen.getByTestId("match-closed-badge")).toHaveTextContent("CLOSED");
    expect(screen.getByTestId("match-apply-closed")).toBeDisabled();
  });

  it("calls onTailorCvClick when button clicked", async () => {
    const user = userEvent.setup();
    const onTailor = vi.fn();
    render(<MatchCard match={baseMatch} onTailorCvClick={onTailor} />);
    await user.click(screen.getByTestId("match-tailor-cv"));
    expect(onTailor).toHaveBeenCalledTimes(1);
  });

  it("renders an external apply link when apply_url is set", () => {
    render(<MatchCard match={baseMatch} />);
    const link = screen.getByTestId("match-apply-external");
    expect(link).toHaveAttribute("href", "https://careers.example.com/apply");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
