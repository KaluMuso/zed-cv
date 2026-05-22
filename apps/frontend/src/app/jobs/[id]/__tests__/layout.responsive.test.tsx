import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JobDetailClient } from "../JobDetailClient";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { Job } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/jobs/j1",
}));

/** Frozen "now" so Posted / Closes-in labels stay stable across CI runs. */
const SNAPSHOT_NOW = new Date("2026-05-21T12:00:00.000Z");

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
  vi.setSystemTime(SNAPSHOT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

const JOB: Job = {
  id: "j1",
  title: "Software Engineer",
  company: "ACME Zambia",
  location: "Lusaka",
  description: "Build APIs for mobile money integrations.",
  description_markdown: "## Role\n\nBuild APIs.",
  employment_type: "full_time",
  work_arrangement: "hybrid",
  salary_min_ngwee: null,
  salary_max_ngwee: null,
  closing_date: "2026-12-01",
  apply_url: "https://example.com/apply",
  apply_email: null,
  source_url: "https://example.com",
  posted_at: "2026-05-01",
  skills: ["python", "fastapi"],
  is_active: true,
};

function atWidth(width: number) {
  return renderWithProviders(
    <div style={{ width, maxWidth: width }} data-testid="viewport-root">
      <JobDetailClient job={JOB} />
    </div>
  );
}

describe("Job detail responsive layout", () => {
  it("matches 380px mobile snapshot", () => {
    const { getByTestId } = atWidth(380);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });

  it("matches 1024px desktop snapshot", () => {
    const { getByTestId } = atWidth(1024);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });
});
