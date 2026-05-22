import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { Toaster } from "@/components/shared/Toaster";
import { FloatingCard } from "@/components/shared/FloatingCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

describe("design system foundation", () => {
  it("renders Toaster, Button variants, Skeleton, and FloatingCard", () => {
    render(
      <>
        <Toaster />
        <div data-testid="buttons">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link</Button>
        </div>
        <Skeleton data-testid="skeleton" className="h-8 w-24" />
        <FloatingCard>
          <span>Floating content</span>
        </FloatingCard>
      </>
    );

    expect(screen.getByRole("button", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Secondary" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Outline" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ghost" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Destructive" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Link" })).toBeInTheDocument();
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    expect(screen.getByText("Floating content")).toBeInTheDocument();
  });

  it("shows loading spinner on Button without collapsing width", () => {
    render(
      <Button variant="primary" loading>
        Save job
      </Button>
    );
    const btn = screen.getByRole("button");
    expect(btn).toHaveAttribute("aria-busy", "true");
    expect(btn).toHaveTextContent("Save job");
  });
});
