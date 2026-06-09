import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { Navbar } from "../Navbar";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

let mockPathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

vi.mock("@/components/ThemeProvider", () => ({
  useTheme: () => ({ dark: false, toggle: vi.fn() }),
}));

vi.mock("@/components/ui/Logo", () => ({
  Logo: () => <span data-testid="logo" />,
}));

vi.mock("@/components/nav/InterviewPrepNav", () => ({
  InterviewPrepNav: () => <a href="/interview-prep">Interview Prep</a>,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  profile: {
    get: vi.fn().mockResolvedValue({
      full_name: "Jane Banda",
      email: "jane@example.com",
      subscription_tier: "professional",
      role: "user",
    }),
  },
  subscription: {
    get: vi.fn().mockResolvedValue({
      matches_used: 5,
      matches_limit: 125,
    }),
  },
}));

import { useAuth } from "@/lib/auth";

const mockedUseAuth = vi.mocked(useAuth);

function desktopPrimaryNav() {
  const centerNav = document.querySelector(".hidden.lg\\:flex.items-center.gap-8");
  if (!centerNav) throw new Error("desktop primary nav not found");
  return centerNav;
}

describe("Navbar primary navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = "/";
    // Reset window size to desktop default
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  it("shows five task-focused links when signed in", () => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: "tok",
      logout: vi.fn(),
      isLoading: false,
      user: { id: "1", phone: "+260971234567" },
      login: vi.fn(),
    });

    render(<Navbar />);

    const links = within(desktopPrimaryNav() as HTMLElement).getAllByRole("link");
    const labels = links.map((l) => l.textContent?.trim());
    expect(labels).toEqual([
      "Jobs",
      "Matches",
      "Applications",
      "Pricing",
      "Interview Prep",
    ]);
  });

  it("shows centered logo only on mobile app shell routes", () => {
    mockPathname = "/jobs";
    // Mock mobile viewport
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 640,
    });

    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: "tok",
      logout: vi.fn(),
      isLoading: false,
      user: { id: "1", phone: "+260971234567" },
      login: vi.fn(),
    });

    render(<Navbar />);

    // On mobile app shell routes, should show minimal navbar with only logo
    expect(screen.getByTestId("logo")).toBeInTheDocument();
    expect(screen.queryByLabelText("Toggle menu")).not.toBeInTheDocument();
    expect(document.querySelector(".hidden.lg\\:flex.items-center.gap-8")).toBeNull();
  });

  it("shows links when signed out", () => {
    mockPathname = "/jobs";
    mockedUseAuth.mockReturnValue({
      isAuthenticated: false,
      token: null,
      logout: vi.fn(),
      isLoading: false,
      user: null,
      login: vi.fn(),
    });

    render(<Navbar />);

    const labels = within(desktopPrimaryNav() as HTMLElement)
      .getAllByRole("link")
      .map((l) => l.textContent?.trim());
    expect(labels).toEqual([
      "Jobs",
      "Matches",
      "Pricing",
    ]);

    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Get started" })).toHaveLength(2);
  });

  it("does not show Dashboard or Profile in primary nav when signed in", () => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: "tok",
      logout: vi.fn(),
      isLoading: false,
      user: { id: "1", phone: "+260971234567" },
      login: vi.fn(),
    });

    render(<Navbar />);

    const labels = within(desktopPrimaryNav() as HTMLElement)
      .getAllByRole("link")
      .map((l) => l.textContent?.trim());
    expect(labels).not.toContain("Dashboard");
    expect(labels).not.toContain("Profile");
  });
});
