import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UserMenuDropdown } from "../UserMenuDropdown";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    onClick,
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: () => void;
  }) => (
    <a href={href} onClick={onClick}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

vi.mock("@/lib/api", () => ({
  inAppNotifications: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: "n1",
          type: "web_push",
          payload: { title: "Strong match", body: "90%", url: "/matches/x" },
          read_at: null,
          created_at: new Date().toISOString(),
        },
      ],
      unread_count: 1,
    }),
    markRead: vi.fn(),
  },
}));

describe("UserMenuDropdown", () => {
  const baseProps = {
    displayName: "Jane Banda",
    tierSubtitle: "Professional · 12/125 matches",
    onClose: vi.fn(),
    onSignOut: vi.fn(),
  };

  it("renders engagement, career, and account sections", () => {
    render(
      <UserMenuDropdown
        {...baseProps}
        subscriptionTier="professional"
        showAdmin={false}
      />,
    );

    expect(screen.getByText("Engagement")).toBeInTheDocument();
    expect(screen.getByText("Career data")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("menuitem", { name: /notifications/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /profile \(cv & skills\)/i })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(screen.getByRole("link", { name: /my matches/i })).toHaveAttribute(
      "href",
      "/matches",
    );
    expect(screen.getByRole("link", { name: /^settings$/i })).toHaveAttribute(
      "href",
      "/settings/account",
    );
  });

  it("shows unread badge on notifications menu item", () => {
    render(
      <UserMenuDropdown
        {...baseProps}
        subscriptionTier="professional"
        unreadCount={3}
      />,
    );
    expect(screen.getByLabelText("3 unread")).toBeInTheDocument();
  });

  it("opens notifications panel when Notifications is clicked", async () => {
    const user = userEvent.setup();
    render(
      <UserMenuDropdown {...baseProps} subscriptionTier="professional" />,
    );
    await user.click(screen.getByRole("menuitem", { name: /notifications/i }));
    expect(await screen.findByText("Strong match")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /notification preferences/i })).toHaveAttribute(
      "href",
      "/settings/notifications",
    );
  });

  it("shows CV Generator for paid tiers only", () => {
    const { rerender } = render(
      <UserMenuDropdown {...baseProps} subscriptionTier="free" showAdmin={false} />,
    );
    expect(screen.queryByRole("link", { name: /cv generator/i })).not.toBeInTheDocument();

    rerender(
      <UserMenuDropdown {...baseProps} subscriptionTier="starter" showAdmin={false} />,
    );
    expect(screen.getByRole("link", { name: /cv generator/i })).toHaveAttribute(
      "href",
      "/profile?tab=cv-generator",
    );
  });

  it("shows Admin for staff", () => {
    render(
      <UserMenuDropdown {...baseProps} subscriptionTier="professional" showAdmin />,
    );
    expect(screen.getByRole("link", { name: /^admin$/i })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("calls onSignOut when Sign out is clicked", async () => {
    const user = userEvent.setup();
    const onSignOut = vi.fn();
    const onClose = vi.fn();
    render(
      <UserMenuDropdown
        {...baseProps}
        onSignOut={onSignOut}
        onClose={onClose}
        subscriptionTier="professional"
      />,
    );
    await user.click(screen.getByRole("menuitem", { name: /sign out/i }));
    expect(onClose).toHaveBeenCalled();
    expect(onSignOut).toHaveBeenCalled();
  });
});
