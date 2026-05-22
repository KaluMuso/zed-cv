import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";

import MatchesPageClient from "../MatchesPageClient";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/renderWithProviders";

class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.IntersectionObserver =
  MockIntersectionObserver as unknown as typeof IntersectionObserver;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/matches",
}));

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

beforeEach(() => {
  localStorage.setItem("zed_cv_token", "jwt");
  localStorage.setItem("zed_cv_user_id", "u1");
  server.use(
    http.get(`${API}/users/me/saved-jobs`, () => HttpResponse.json({ job_ids: [] })),
    http.get(`${API}/matches`, () =>
      HttpResponse.json({ matches: [], remaining_quota: 10 })
    ),
    http.get(`${API}/subscription`, () =>
      HttpResponse.json({ tier: "starter", matches_used: 0, matches_limit: 50 })
    ),
    http.get(`${API}/preferences`, () =>
      HttpResponse.json({
        target_roles: [],
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
        auto_match_enabled: false,
        notification_channels: { whatsapp: true, email: true },
      })
    ),
    http.get(`${API}/profile`, () =>
      HttpResponse.json({
        id: "u1",
        phone: "+260971234567",
        full_name: "Test",
        cv_uploaded: true,
        skills: [],
        subscription_tier: "starter",
      })
    )
  );
});

function atWidth(width: number) {
  return renderWithProviders(
    <div style={{ width, maxWidth: width }} data-testid="viewport-root">
      <MatchesPageClient />
    </div>
  );
}

describe("MatchesPage responsive layout", () => {
  it("matches 380px mobile snapshot", () => {
    const { getByTestId } = atWidth(380);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });

  it("matches 1024px desktop snapshot", () => {
    const { getByTestId } = atWidth(1024);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });
});
