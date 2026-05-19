import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import MatchesPage from "../page";
import { AuthProvider } from "@/lib/auth";
import { server } from "@/test/msw/server";

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
  triggerStatus?: number;
}) {
  const {
    matches = [MATCH_OBJ],
    cvUploaded = false,
    onTrigger,
    triggerStatus = 200,
  } = opts;
  server.use(
    http.get(`${API}/matches`, () =>
      HttpResponse.json({ matches, remaining_quota: 10 })
    ),
    http.get(`${API}/subscription`, () =>
      HttpResponse.json({ tier: "starter", matches_used: 5, matches_limit: 25 })
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
    http.post(`${API}/matches/trigger`, () => {
      onTrigger?.();
      return HttpResponse.json(
        { message: "ok", estimated_seconds: 0 },
        { status: triggerStatus }
      );
    }),
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
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    const buttons = await screen.findAllByText("Refresh matches", {}, { timeout: 5000 });
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("calls trigger on click", async () => {
    let triggered = false;
    withHandlers({ matches: [MATCH_OBJ], onTrigger: () => { triggered = true; } });
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    const buttons = await screen.findAllByText("Refresh matches", {}, { timeout: 5000 });
    await userEvent.click(buttons[0]);
    await waitFor(() => expect(triggered).toBe(true));
  });

  it("disables button while refreshing", async () => {
    withHandlers({ matches: [MATCH_OBJ] });
    server.use(
      http.post(`${API}/matches/trigger`, async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({ message: "ok", estimated_seconds: 0 });
      }),
    );
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    const buttons = await screen.findAllByText("Refresh matches", {}, { timeout: 5000 });
    await userEvent.click(buttons[0]);
    const refreshingBtns = screen.getAllByText("Refreshing\u2026");
    expect(refreshingBtns[0]).toBeDisabled();
  });
});

describe("Auto-trigger", () => {
  it("fires when empty matches + CV uploaded", async () => {
    let triggered = false;
    withHandlers({ matches: [], cvUploaded: true, onTrigger: () => { triggered = true; } });
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    await waitFor(() => expect(triggered).toBe(true), { timeout: 5000 });
  });

  it("does NOT fire when no CV", async () => {
    let triggered = false;
    withHandlers({ matches: [], cvUploaded: false, onTrigger: () => { triggered = true; } });
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    await screen.findByText("No matches yet", {}, { timeout: 5000 });
    expect(triggered).toBe(false);
  });

  it("does NOT fire when matches exist", async () => {
    let triggered = false;
    withHandlers({ matches: [MATCH_OBJ], cvUploaded: true, onTrigger: () => { triggered = true; } });
    render(<AuthProvider><MatchesPage /></AuthProvider>);
    await screen.findByText("Engineer", {}, { timeout: 5000 });
    expect(triggered).toBe(false);
  });
});
