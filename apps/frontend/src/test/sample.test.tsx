import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

describe("Vitest infrastructure sentinel", () => {
  it("renders a button and queries it", () => {
    render(<button type="button">Hello</button>);
    expect(screen.getByRole("button", { name: "Hello" })).toBeInTheDocument();
  });
});
