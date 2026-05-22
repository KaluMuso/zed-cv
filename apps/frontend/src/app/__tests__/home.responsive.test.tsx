import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
globalThis.IntersectionObserver =
  MockIntersectionObserver as unknown as typeof IntersectionObserver;

import HomePageClient from "../HomePageClient";
import { renderWithProviders } from "@/test/renderWithProviders";
import { server } from "@/test/msw/server";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

beforeEach(() => {
  server.use(
    http.get(`${API}/stats/public`, () =>
      HttpResponse.json({
        jobs_active: 500,
        avg_skills_matched: 7,
        hours_saved_total: 1000,
      })
    )
  );
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/hooks/useScrollReveal", () => ({
  useScrollReveal: () => undefined,
}));

function atWidth(width: number, ui: React.ReactElement) {
  return renderWithProviders(
    <div style={{ width, maxWidth: width }} data-testid="viewport-root">
      {ui}
    </div>
  );
}

describe("HomePage responsive layout", () => {
  it("matches 380px mobile snapshot", () => {
    const { getByTestId } = atWidth(380, <HomePageClient />);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });

  it("matches 1024px desktop snapshot", () => {
    const { getByTestId } = atWidth(1024, <HomePageClient />);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });
});
