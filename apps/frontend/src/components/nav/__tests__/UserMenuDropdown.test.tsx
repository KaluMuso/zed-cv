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
    expect(screen.getByRole("link", { name: /notifications/i })).toHaveAttribute(
      "href",
      "/settings/notifications",
    );
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
