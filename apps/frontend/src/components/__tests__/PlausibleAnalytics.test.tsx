import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { PlausibleAnalytics } from "@/components/PlausibleAnalytics";

vi.mock("next/script", () => ({
  default: (props: Record<string, unknown>) => (
    <script data-testid="plausible-script" {...props} />
  ),
}));

describe("PlausibleAnalytics", () => {
  const prev = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
  });

  afterEach(() => {
    if (prev === undefined) {
      delete process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
    } else {
      process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN = prev;
    }
  });

  it("renders nothing when domain env is unset", () => {
    const { container } = render(<PlausibleAnalytics />);
    expect(container.firstChild).toBeNull();
  });

  it("loads Plausible script when domain env is set", () => {
    process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN = "zedapply.com";
    const { getByTestId } = render(<PlausibleAnalytics />);
    const el = getByTestId("plausible-script");
    expect(el.getAttribute("data-domain")).toBe("zedapply.com");
    expect(el.getAttribute("src")).toBe("https://plausible.io/js/script.js");
  });
});
