import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MAIN_CONTENT_ID, SkipToContent } from "../SkipToContent";

describe("SkipToContent", () => {
  it("links to the main content landmark", () => {
    render(<SkipToContent />);
    const link = screen.getByRole("link", { name: /skip to main content/i });
    expect(link.getAttribute("href")).toBe(`#${MAIN_CONTENT_ID}`);
  });
});
