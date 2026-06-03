import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
globalThis.IntersectionObserver =
  MockIntersectionObserver as unknown as typeof IntersectionObserver;

vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div {...props}>{children}</div>
    ),
    circle: (props: Record<string, unknown>) => <circle {...props} />,
  },
  useReducedMotion: () => true,
}));

vi.mock("@/components/marketing/ScoreBreakdownMockup", () => ({
  ScoreBreakdownMockup: () => (
    <div data-testid="score-breakdown-mockup">Score breakdown mockup</div>
  ),
}));

import {
  SCORE_MATH_SECTION_TEXT,
  ScoreMathSection,
} from "../ScoreMathSection";

describe("ScoreMathSection contrast classes", () => {
  it("uses semantic foreground tokens for headings and body copy", () => {
    render(<ScoreMathSection />);

    expect(screen.getByRole("heading", { level: 2 })).toHaveClass(
      "text-foreground",
    );
    expect(screen.getByText(/§ 02 \/ Transparent scoring/i)).toHaveClass(
      "text-muted-foreground",
    );
    expect(
      screen.getByText(/No black box\. Every score breaks down/i),
    ).toHaveClass("text-muted-foreground");
  });

  it("exports stable semantic class map for marketing sections", () => {
    expect(SCORE_MATH_SECTION_TEXT.heading).toContain("text-foreground");
    expect(SCORE_MATH_SECTION_TEXT.eyebrow).toContain("text-muted-foreground");
    expect(SCORE_MATH_SECTION_TEXT.lead).toContain("text-muted-foreground");
    expect(SCORE_MATH_SECTION_TEXT.bulletTitle).toContain("text-foreground");
    expect(SCORE_MATH_SECTION_TEXT.bulletBody).toContain(
      "text-muted-foreground",
    );
  });
});
