import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import JobsPageClient from "../JobsPageClient";
import { AuthProvider } from "@/lib/auth";
import { server } from "@/test/msw/server";

// Counter relies on IntersectionObserver which jsdom doesn't ship.
// We don't care about the count-up animation here — replace with a
// passthrough so the page can mount.
vi.mock("@/components/ui/Counter", () => ({
  Counter: ({ to }: { to: number }) => <span>{to}</span>,
}));

// next/navigation isn't available in the jsdom env. Mock the surface
// the page uses: useRouter().replace, usePathname, useSearchParams.
vi.mock("next/navigation", () => {
  let params = new URLSearchParams();
  const replace = vi.fn((href: string) => {
    const query = href.includes("?") ? href.split("?")[1] : "";
    params = new URLSearchParams(query);
  });
  return {
    useRouter: () => ({
      replace,
      push: vi.fn(),
      prefetch: vi.fn(),
      refresh: vi.fn(),
    }),
    usePathname: () => "/jobs",
    useSearchParams: () => params,
  };
});

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Capture every URL the page hits so each test can assert which filters
// went out as query params. Reset between tests.
let requestedUrls: string[] = [];

beforeEach(() => {
  requestedUrls = [];
  server.use(
    http.get(`${API_BASE}/users/me/saved-jobs`, () =>
      HttpResponse.json({ jobs: [] })
    ),
    http.get(`${API_BASE}/jobs`, ({ request }) => {
      requestedUrls.push(request.url);
      return HttpResponse.json({
        jobs: [
          {
            id: "job-1",
            title: "Senior Accountant",
            company: "Acme Ltd",
            location: "Lusaka",
            skills: ["accounting"],
            description: "Lead the finance team.",
            posted_at: new Date().toISOString(),
            closing_date: null,
            salary_min: null,
            salary_max: null,
            source: "manual",
            source_url: null,
            apply_url: null,
            apply_email: null,
            employment_type: "full_time",
            work_arrangement: "on_site",
            benefits: [],
            tools_tech_stack: [],
          },
        ],
        total: 1,
        page: 1,
        pages: 1,
      });
    }),
  );
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

function renderJobsPage() {
  return render(
    <AuthProvider>
      <JobsPageClient />
    </AuthProvider>,
  );
}

function lastRequest(): URL {
  expect(requestedUrls.length).toBeGreaterThan(0);
  return new URL(requestedUrls[requestedUrls.length - 1]);
}

describe("/jobs page filters", () => {
  it("issues an initial fetch on mount", async () => {
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));
    const url = lastRequest();
    // Default sort is "recent"; no other filters set.
    expect(url.searchParams.get("sort")).toBe("recent");
    expect(url.searchParams.get("search")).toBeNull();
    expect(url.searchParams.get("location")).toBeNull();
    expect(url.searchParams.get("employment_type")).toBeNull();
    expect(url.searchParams.get("work_arrangement")).toBeNull();
  });

  it(
    "debounces search input (300ms) before calling the API with `search`",
    async () => {
      renderJobsPage();
      await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));
      const nAfterMount = requestedUrls.length;

      const user = userEvent.setup();
      await user.type(
        screen.getByRole("textbox", { name: /search jobs/i }),
        "accountant",
      );

      expect(requestedUrls.length).toBe(nAfterMount);

      await act(async () => {
        await new Promise((r) => setTimeout(r, 350));
      });

      await waitFor(() => {
        expect(requestedUrls.length).toBeGreaterThan(nAfterMount);
        expect(lastRequest().searchParams.get("search")).toBe("accountant");
      });
    },
    10_000,
  );

  it("pressing Enter in the search field commits the query immediately", async () => {
    const user = userEvent.setup();
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    const field = screen.getByRole("textbox", { name: /search jobs/i });
    await user.type(field, "engineer{Enter}");

    await waitFor(() => {
      expect(lastRequest().searchParams.get("search")).toBe("engineer");
    });
  });

  it("changing the location dropdown forwards `location`", async () => {
    const user = userEvent.setup();
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /location/i }),
      "Lusaka",
    );

    await waitFor(() => {
      expect(lastRequest().searchParams.get("location")).toBe("Lusaka");
    });
  });

  // Skipped while FILTERS_AVAILABLE.employmentType is false in
  // jobs/page.tsx — the dropdown isn't rendered today because every
  // active job has NULL for employment_type. Re-enable when Path B
  // ships and the flag flips to true.
  it.skip("selecting an employment type forwards `employment_type`", async () => {
    const user = userEvent.setup();
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /employment type/i }),
      "full_time",
    );

    await waitFor(() => {
      expect(lastRequest().searchParams.get("employment_type")).toBe(
        "full_time",
      );
    });
  });

  // Skipped while FILTERS_AVAILABLE.workArrangement is false in
  // jobs/page.tsx (see sibling skip above).
  it.skip("selecting a work arrangement forwards `work_arrangement`", async () => {
    const user = userEvent.setup();
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /work arrangement/i }),
      "remote",
    );

    await waitFor(() => {
      expect(lastRequest().searchParams.get("work_arrangement")).toBe("remote");
    });
  });

  // Skipped while FILTERS_AVAILABLE.{employmentType,workArrangement}
  // are false in jobs/page.tsx. The location-only composition path is
  // already covered by the location test above.
  it.skip("multiple filters compose into a single request", async () => {
    const user = userEvent.setup();
    renderJobsPage();
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /location/i }),
      "Lusaka",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: /employment type/i }),
      "full_time",
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: /work arrangement/i }),
      "remote",
    );

    await waitFor(() => {
      const url = lastRequest();
      expect(url.searchParams.get("location")).toBe("Lusaka");
      expect(url.searchParams.get("employment_type")).toBe("full_time");
      expect(url.searchParams.get("work_arrangement")).toBe("remote");
    });
  });

  it("renders the 'no jobs match' empty state when the API returns no rows", async () => {
    server.use(
      http.get(`${API_BASE}/jobs`, () =>
        HttpResponse.json({ jobs: [], total: 0, page: 1, pages: 0 }),
      ),
    );
    const user = userEvent.setup();
    renderJobsPage();

    await user.selectOptions(
      screen.getByRole("combobox", { name: /location/i }),
      "Kabwe",
    );

    expect(
      await screen.findByRole("heading", { name: /no jobs match your filters/i }),
    ).toBeInTheDocument();
  });
});
