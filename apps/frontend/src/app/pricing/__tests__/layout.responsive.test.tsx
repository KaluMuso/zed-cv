import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";

import PricingPage from "../page";
import { renderWithProviders } from "@/test/renderWithProviders";
import { server } from "@/test/msw/server";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

beforeEach(() => {
  server.use(
    http.get(`${API}/tiers`, () =>
      HttpResponse.json({
        tiers: [
          {
            tier: "free",
            display_name: "Free",
            price_ngwee: 0,
            matches_limit: 10,
            sort_order: 0,
            billing_period_days: 30,
            promotion_active: null,
            checkout_price_ngwee: null,
          },
          {
            tier: "starter",
            display_name: "Starter",
            price_ngwee: 12500,
            matches_limit: 50,
            sort_order: 1,
            billing_period_days: 30,
            promotion_active: false,
            checkout_price_ngwee: null,
          },
          {
            tier: "professional",
            display_name: "Professional",
            price_ngwee: 25000,
            matches_limit: 125,
            sort_order: 2,
            billing_period_days: 30,
            promotion_active: false,
            checkout_price_ngwee: null,
          },
          {
            tier: "super_standard",
            display_name: "Super Standard",
            price_ngwee: 50000,
            matches_limit: 99999,
            sort_order: 3,
            billing_period_days: 30,
            promotion_active: false,
            checkout_price_ngwee: null,
          },
          {
            tier: "starter",
            display_name: "Starter (Annual)",
            price_ngwee: 105000,
            matches_limit: 50,
            sort_order: 1,
            billing_period_days: 365,
            promotion_active: null,
            checkout_price_ngwee: null,
          },
          {
            tier: "professional",
            display_name: "Professional (Annual)",
            price_ngwee: 210000,
            matches_limit: 125,
            sort_order: 2,
            billing_period_days: 365,
            promotion_active: null,
            checkout_price_ngwee: null,
          },
          {
            tier: "super_standard",
            display_name: "Super Standard (Annual)",
            price_ngwee: 420000,
            matches_limit: 99999,
            sort_order: 3,
            billing_period_days: 365,
            promotion_active: null,
            checkout_price_ngwee: null,
          },
        ],
      }),
    ),
    http.get(`${API}/subscription`, () =>
      HttpResponse.json({ tier: "free", status: "active" }),
    ),
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
    isLoading: false,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("next/script", () => ({
  default: () => null,
}));

describe("PricingPage Monthly/Yearly toggle", () => {
  it("defaults to Monthly (does not surprise users into annual billing)", () => {
    const { getByRole } = renderWithProviders(<PricingPage />);
    const monthlyTab = getByRole("button", { name: /^monthly$/i });
    const yearlyTab = getByRole("button", { name: /yearly/i });

    // Monthly is the visually-selected tab — its background changes when
    // selected. We assert via class membership rather than the exact CSS
    // var name so a stylistic refactor doesn't break the test.
    expect(monthlyTab.className).toMatch(/bg-\[var\(--ink\)\]/);
    expect(yearlyTab.className).not.toMatch(/bg-\[var\(--ink\)\]/);
  });

  it("advertises the actual 30% annual saving on the Yearly toggle badge", () => {
    const { getByText } = renderWithProviders(<PricingPage />);
    // The exact discount matters — 20% understates the offer (K125 × 12 →
    // K1050 is 30% off, see PR #310). Don't accept "Save 20%" silently
    // again.
    expect(getByText(/save 30%/i)).toBeTruthy();
  });

  it("swaps the launch-discount banner when the Yearly tab is selected", async () => {
    const user = userEvent.setup();
    const { findByText, queryByText, getByRole } = renderWithProviders(
      <PricingPage />,
    );

    // Monthly tab default: 50%-off banner is visible.
    expect(
      await findByText(/first month: 50% off for paid tiers/i),
    ).toBeTruthy();

    // Click Yearly. The 50%-off banner must disappear (PR #306 skips the
    // welcome promo for annual rows; surfacing it on the Yearly tab
    // would mislead users into expecting K525 at checkout for an annual
    // plan).
    await user.click(getByRole("button", { name: /yearly/i }));

    expect(queryByText(/first month: 50% off for paid tiers/i)).toBeNull();
    expect(
      await findByText(/pay annually and save 30%/i),
    ).toBeTruthy();
  });
});
