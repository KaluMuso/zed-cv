import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobDescription } from "../JobDescription";

describe("JobDescription", () => {
  it("renders structured section cards when section fields are present", () => {
    render(
      <JobDescription
        description="Full body"
        sections={{
          section_responsibilities: "Manage stock.",
          section_requirements: "Grade 12.",
        }}
      />,
    );
    expect(screen.getByText("Responsibilities")).toBeInTheDocument();
    expect(screen.getByText("Requirements")).toBeInTheDocument();
    expect(screen.getByText("Manage stock.")).toBeInTheDocument();
  });

  it("falls back to markdown when no structured sections", () => {
    render(
      <JobDescription
        description="Plain description body"
        descriptionMarkdown="## Role\n\nBuild APIs."
      />,
    );
    expect(screen.getByText(/Build APIs/)).toBeInTheDocument();
  });
});
