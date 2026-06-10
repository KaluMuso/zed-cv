import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { AuthProvider } from "@/lib/auth";

import PricingPage from "../page";
import { renderWithProviders } from "@/test/renderWithProviders";
import { server } from "@/test/msw/server";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

beforeEach(() => {
  server.use(
    http.get(`${API}/tiers`, () =>
      HttpResponse.json({
        tiers: [
          { tier: "free", display_name: "Free", price_ngwee: 0, matches_limit: 10, sort_order: 0 },
          { tier: "starter", display_name: "Starter", price_ngwee: 12500, matches_limit: 50, sort_order: 1 },
          { tier: "professional", display_name: "Professional", price_ngwee: 25000, matches_limit: 125, sort_order: 2 },
          { tier: "super_standard", display_name: "Super Standard", price_ngwee: 50000, matches_limit: 99999, sort_order: 3 },
        ],
      })
    )
  );
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/pricing",
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    token: "fake-token",
    user: { id: "user-123", phone: "+260971234567" },
    isAuthenticated: true,
  }),
  AuthProvider: ({ children }: any) => <>{children}</>,
}));

vi.mock("next/script", () => ({
  default: () => null,
}));

function atWidth(width: number, ui: React.ReactElement) {
  return renderWithProviders(
    <div style={{ width, maxWidth: width }} data-testid="viewport-root">
      {ui}
    </div>
  );
}

describe("PricingPage responsive layout", () => {
  it("matches 380px mobile snapshot", () => {
    const { getByTestId } = atWidth(380, <PricingPage />);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });

  it("matches 1024px desktop snapshot", () => {
    const { getByTestId } = atWidth(1024, <PricingPage />);
    expect(getByTestId("viewport-root")).toMatchSnapshot();
  });
});
