import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { PlausibleAnalytics } from "@/components/PlausibleAnalytics";

vi.mock("next/script", () => ({
  default: (props: Record<string, unknown>) => {
    const { children, ...rest } = props;
    return (
      <script data-testid={rest.id ? "plausible-init" : "plausible-script"} {...rest}>
        {children}
      </script>
    );
  },
}));

describe("PlausibleAnalytics", () => {
  const prevDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
  const prevScriptUrl = process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
    delete process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL;
  });

  afterEach(() => {
    if (prevDomain === undefined) {
      delete process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
    } else {
      process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN = prevDomain;
    }
    if (prevScriptUrl === undefined) {
      delete process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL;
    } else {
      process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL = prevScriptUrl;
    }
  });

  it("renders nothing when env is unset", () => {
    const { container } = render(<PlausibleAnalytics />);
    expect(container.firstChild).toBeNull();
  });

  it("loads site-specific Plausible script when SCRIPT_URL is set", () => {
    process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_URL =
      "https://plausible.io/js/pa-gue6dHinYctK6EwKQzVZw.js";
    const { getAllByTestId } = render(<PlausibleAnalytics />);
    const scripts = getAllByTestId("plausible-script");
    expect(scripts).toHaveLength(1);
    expect(scripts[0]?.getAttribute("src")).toBe(
      "https://plausible.io/js/pa-gue6dHinYctK6EwKQzVZw.js",
    );
    expect(getAllByTestId("plausible-init")).toHaveLength(1);
  });

  it("loads legacy script.js when only domain env is set", () => {
    process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN = "zedapply.com";
    const { getByTestId, queryByTestId } = render(<PlausibleAnalytics />);
    const el = getByTestId("plausible-script");
    expect(el.getAttribute("data-domain")).toBe("zedapply.com");
    expect(el.getAttribute("src")).toBe("https://plausible.io/js/script.js");
    expect(queryByTestId("plausible-init")).toBeNull();
  });
});
