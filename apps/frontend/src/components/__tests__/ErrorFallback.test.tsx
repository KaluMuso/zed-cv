import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorFallback } from "@/components/ErrorFallback";

describe("ErrorFallback", () => {
  const reset = vi.fn();

  beforeEach(() => {
    reset.mockClear();
  });

  it("renders branded copy, digest ref, and actions", () => {
    const error = Object.assign(new Error("boom"), { digest: "abc123" });
    render(<ErrorFallback error={error} reset={reset} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText((_, el) => el?.textContent === "ZedApply")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go home/i })).toHaveAttribute("href", "/");
  });

  it("calls reset when Try again is clicked", () => {
    render(
      <ErrorFallback error={new Error("x")} reset={reset} />
    );
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("shows error details toggle in development", () => {
    const prev = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";
    const error = new Error("debug message");
    error.stack = "Error: debug message\n    at test";

    render(<ErrorFallback error={error} reset={reset} />);
    expect(screen.getByRole("button", { name: /show error details/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /show error details/i }));
    expect(screen.getByText(/debug message/)).toBeInTheDocument();

    process.env.NODE_ENV = prev;
  });
});
