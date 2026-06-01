import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import NewAdminJobPage from "./page";
import { AdminGuard } from "@/app/admin/admin-guard";
import { AuthProvider } from "@/lib/auth";
import { server } from "@/test/msw/server";

// next/navigation is unavailable in Vitest's jsdom env (the App Router
// hooks pull from a request context that only exists at runtime). Mock
// the surface we need; the rest of the page doesn't touch routing.
const routerReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: routerReplace,
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
}));

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function profileEndpoint(role: "admin" | "superadmin" | "user") {
  return http.get(`${API_BASE}/profile`, () =>
    HttpResponse.json({
      id: "u-1",
      phone: "+260971234567",
      full_name: "Test Admin",
      email: null,
      skills: [],
      cv_uploaded: false,
      subscription_tier: "free",
      role,
    }),
  );
}

function adminStatsEndpoint() {
  return http.get(`${API_BASE}/admin/stats`, () =>
    HttpResponse.json({ pending_review_count: 0 }),
  );
}

function renderGuarded() {
  return render(
    <AuthProvider>
      <AdminGuard>
        <NewAdminJobPage />
      </AdminGuard>
    </AuthProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  // AuthProvider hydrates from localStorage on mount — seed a token so
  // the guard treats the user as authenticated and runs the role check.
  window.localStorage.setItem("zed_cv_token", "test-token");
  window.localStorage.setItem("zed_cv_user_id", "u-1");
  routerReplace.mockClear();
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("/admin/jobs/new page", () => {
  it("redirects non-admin users away", async () => {
    server.use(profileEndpoint("user"));
    renderGuarded();

    // AdminGuard calls router.replace('/') for authenticated non-admins.
    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith("/");
    });

    // Wizard heading is NOT rendered for non-admins.
    expect(
      screen.queryByRole("heading", { name: /new job/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the manual form for admin users", async () => {
    server.use(profileEndpoint("admin"), adminStatsEndpoint());
    renderGuarded();

    expect(
      await screen.findByRole("heading", { name: /new job/i, level: 1 }),
    ).toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
    expect(screen.getByTestId("admin-job-description-md")).toBeInTheDocument();
  });
});
