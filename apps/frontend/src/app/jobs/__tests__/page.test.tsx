import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import JobsPage from "../page";
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
  const params = new URLSearchParams();
  return {
    useRouter: () => ({
      replace: vi.fn(),
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
  cleanup();
});

function lastRequest(): URL {
  expect(requestedUrls.length).toBeGreaterThan(0);
  return new URL(requestedUrls[requestedUrls.length - 1]);
}

describe("/jobs page filters", () => {
  it("issues an initial fetch on mount", async () => {
    render(<JobsPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));
    const url = lastRequest();
    // Default sort is "recent"; no other filters set.
    expect(url.searchParams.get("sort")).toBe("recent");
    expect(url.searchParams.get("search")).toBeNull();
    expect(url.searchParams.get("location")).toBeNull();
    expect(url.searchParams.get("employment_type")).toBeNull();
    expect(url.searchParams.get("work_arrangement")).toBeNull();
  });

  it("submitting the search form forwards `search` to the API", async () => {
    const user = userEvent.setup();
    render(<JobsPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.type(
      screen.getByRole("textbox", { name: /search jobs/i }),
      "accountant",
    );
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => {
      expect(lastRequest().searchParams.get("search")).toBe("accountant");
    });
  });

  it("changing the location dropdown forwards `location`", async () => {
    const user = userEvent.setup();
    render(<JobsPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /location/i }),
      "Lusaka",
    );

    await waitFor(() => {
      expect(lastRequest().searchParams.get("location")).toBe("Lusaka");
    });
  });

  it("selecting an employment type forwards `employment_type`", async () => {
    const user = userEvent.setup();
    render(<JobsPage />);
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

  it("selecting a work arrangement forwards `work_arrangement`", async () => {
    const user = userEvent.setup();
    render(<JobsPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));

    await user.selectOptions(
      screen.getByRole("combobox", { name: /work arrangement/i }),
      "remote",
    );

    await waitFor(() => {
      expect(lastRequest().searchParams.get("work_arrangement")).toBe("remote");
    });
  });

  it("multiple filters compose into a single request", async () => {
    const user = userEvent.setup();
    render(<JobsPage />);
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
    render(<JobsPage />);

    await user.selectOptions(
      screen.getByRole("combobox", { name: /location/i }),
      "Kabwe",
    );

    expect(
      await screen.findByRole("heading", { name: /no jobs match your filters/i }),
    ).toBeInTheDocument();
  });
});
