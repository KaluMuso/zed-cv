import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobDetailPremiumActions } from "@/components/jobs/JobDetailPremiumActions";

describe("JobDetailPremiumActions", () => {
  it("shows purple upgrade links for free tier", () => {
    render(
      <JobDetailPremiumActions
        subscriptionTier="free"
        jobId="j1"
        jobTitle="Engineer"
        company="ACME"
        onCoverLetterClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("job-detail-upgrade-cover_letter")).toBeInTheDocument();
    expect(screen.getByTestId("job-detail-upgrade-tailor_cv")).toBeInTheDocument();
    expect(screen.getByText(/Generate cover letter/i)).toBeInTheDocument();
    expect(screen.getByText(/Tailored CV/i)).toBeInTheDocument();
    expect(screen.queryByTestId("job-detail-cover-letter")).not.toBeInTheDocument();
  });

  it("shows live actions for professional tier", () => {
    render(
      <JobDetailPremiumActions
        subscriptionTier="professional"
        jobId="j1"
        jobTitle="Engineer"
        company="ACME"
        onCoverLetterClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("job-detail-cover-letter")).toBeInTheDocument();
    expect(screen.getByTestId("job-detail-tailored-cv")).toBeInTheDocument();
    expect(screen.queryByTestId("job-detail-upgrade-cover_letter")).not.toBeInTheDocument();
  });
});
