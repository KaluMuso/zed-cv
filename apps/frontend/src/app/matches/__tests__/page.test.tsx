import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import MatchesPageClient from "../MatchesPageClient";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/renderWithProviders";

class MockIntersectionObserver {
  observe() { /* noop */ }
  unobserve() { /* noop */ }
  disconnect() { /* noop */ }
}
globalThis.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  refresh: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
};
vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/matches",
}));

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const MATCH_OBJ = {
  id: "m1",
  score: 85,
  vector_score: 80,
  skill_score: 90,
  bonus_score: 5,
  matched_skills: ["python"],
  missing_skills: [],
  explanation: null,
  created_at: "2026-05-18T00:00:00Z",
  job: {
    id: "j1",
    title: "Engineer",
    company: "ACME",
    location: "Lusaka",
    closing_date: null,
    apply_url: "https://x.com",
    apply_email: null,
    source_url: null,
  },
};

function withHandlers(opts: {
  matches?: unknown[];
  cvUploaded?: boolean;
  onTrigger?: () => void;
  onAutoPatch?: (body: unknown) => void;
  triggerStatus?: number;
}) {
  const {
    matches = [MATCH_OBJ],
    cvUploaded = false,
    onTrigger,
    onAutoPatch,
    triggerStatus = 200,
  } = opts;
  server.use(
    http.get(`${API}/users/me/saved-jobs`, () => HttpResponse.json({ jobs: [] })),
    http.get(`${API}/matches`, () =>
      HttpResponse.json({ matches, remaining_quota: 10 })
    ),
    http.get(`${API}/subscription`, () =>
      HttpResponse.json({ tier: "starter", matches_used: 5, matches_limit: 50 })
    ),
    http.get(`${API}/preferences`, () =>
      HttpResponse.json({
        target_roles: ["dev"],
        salary_min: null,
        salary_max: null,
        salary_frequency: null,
        preferred_work_arrangement: null,
        acceptable_regions: [],
        preferred_industries: [],
        languages: [],
      })
    ),
    http.get(`${API}/users/me/preferences/auto-match`, () =>
      HttpResponse.json({
        auto_match_enabled: true,
        notification_channels: { whatsapp: true, email: true },
      })
    ),
    http.patch(`${API}/users/me/preferences/auto-match`, async ({ request }) => {
      const body = await request.json();
      onAutoPatch?.(body);
      return HttpResponse.json({
        auto_match_enabled: Boolean(
          (body as { auto_match_enabled?: boolean }).auto_match_enabled
        ),
        notification_channels: { whatsapp: true, email: true },
      });
    }),
    http.get(`${API}/profile`, () =>
      HttpResponse.json({
        id: "u1",
        phone: "+260971234567",
        full_name: "T",
        email: null,
        skills: [],
        cv_uploaded: cvUploaded,
        subscription_tier: "starter",
      })
    ),
    http.post(`${API}/matches/refresh`, () => {
      onTrigger?.();
      return HttpResponse.json(
        {
          matches,
          remaining_quota: 10,
          from_cache: true,
          last_batch_run_at: "2026-05-22T10:00:00Z",
        },
        { status: triggerStatus }
      );
    }),
    http.get(`${API}/users/me/saved-jobs`, () =>
      HttpResponse.json({ job_ids: [] })
    ),
  );
}

beforeEach(() => {
  localStorage.setItem("zed_cv_token", "jwt");
  localStorage.setItem("zed_cv_user_id", "u1");
});
afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("Refresh button", () => {
  it("renders when matches exist", async () => {
    withHandlers({ matches: [MATCH_OBJ], cvUploaded: false });
    renderWithProviders(<MatchesPageClient />);
    const buttons = await screen.findAllByRole("button", { name: /refresh matches/i }, { timeout: 5000 });
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("calls refresh on click", async () => {
    let triggered = false;
    withHandlers({ matches: [MATCH_OBJ], onTrigger: () => { triggered = true; } });
    renderWithProviders(<MatchesPageClient />);
    const buttons = await screen.findAllByRole("button", { name: /refresh matches/i }, { timeout: 5000 });
    await userEvent.click(buttons[0]);
    await waitFor(() => expect(triggered).toBe(true));
  });

  it("disables button while refreshing", async () => {
    withHandlers({ matches: [MATCH_OBJ] });
    server.use(
      http.post(`${API}/matches/refresh`, async () => {
        await new Promise((r) => setTimeout(r, 400));
        return HttpResponse.json({
          matches: [MATCH_OBJ],
          remaining_quota: 10,
          from_cache: true,
        });
      }),
    );
    renderWithProviders(<MatchesPageClient />);
    const buttons = await screen.findAllByRole("button", { name: /refresh matches/i }, { timeout: 5000 });
    await userEvent.click(buttons[0]);
    const refreshingBtns = screen.getAllByRole("button", { name: /refreshing/i });
    expect(refreshingBtns[0]).toBeDisabled();
  });
});

describe("Auto-trigger", () => {
  it("fires when empty matches + CV uploaded", async () => {
    let triggered = false;
    withHandlers({ matches: [], cvUploaded: true, onTrigger: () => { triggered = true; } });
    renderWithProviders(<MatchesPageClient />);
    await waitFor(() => expect(triggered).toBe(true), { timeout: 5000 });
  });

  it("does NOT fire when no CV", async () => {
    let triggered = false;
    withHandlers({ matches: [], cvUploaded: false, onTrigger: () => { triggered = true; } });
    renderWithProviders(<MatchesPageClient />);
    await screen.findByText("No matches yet", {}, { timeout: 5000 });
    expect(triggered).toBe(false);
  });

  it("does NOT fire when matches exist", async () => {
    let triggered = false;
    withHandlers({ matches: [MATCH_OBJ], cvUploaded: true, onTrigger: () => { triggered = true; } });
    renderWithProviders(<MatchesPageClient />);
    await screen.findByText("Engineer", {}, { timeout: 5000 });
    expect(triggered).toBe(false);
  });
});

describe("Apply modal", () => {
  it("opens the apply modal instead of an external apply link", async () => {
    const noApply = {
      ...MATCH_OBJ,
      job: {
        ...MATCH_OBJ.job,
        apply_url: null,
        apply_email: null,
        source_url: "https://example.com/jobs/123",
      },
    };
    withHandlers({ matches: [noApply] });
    renderWithProviders(<MatchesPageClient />);
    const applyBtn = await screen.findByRole("button", { name: /^apply$/i }, { timeout: 5000 });
    await userEvent.click(applyBtn);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/how to apply/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /apply via source/i })).not.toBeInTheDocument();
  });

  it("shows guidance when no contact methods are available", async () => {
    const deadEnd = {
      ...MATCH_OBJ,
      job: {
        ...MATCH_OBJ.job,
        apply_url: null,
        apply_email: null,
        source_url: null,
        description: "Plain role with no contact lines.",
      },
    };
    withHandlers({ matches: [deadEnd] });
    renderWithProviders(<MatchesPageClient />);
    const applyBtn = await screen.findByRole("button", { name: /^apply$/i }, { timeout: 5000 });
    await userEvent.click(applyBtn);
    expect(
      await screen.findByText(/no direct contact details were listed/i),
    ).toBeInTheDocument();
  });
});

describe("Auto-match toggle", () => {
  it("calls the auto-match preference endpoint", async () => {
    let patched: unknown = null;
    withHandlers({
      matches: [MATCH_OBJ],
      onAutoPatch: (body) => {
        patched = body;
      },
    });
    renderWithProviders(<MatchesPageClient />);
    const toggle = await screen.findByLabelText("Auto-match", {}, { timeout: 5000 });
    await userEvent.click(toggle);
    await waitFor(() => {
      expect(patched).toEqual({ auto_match_enabled: false });
    });
  });
});
