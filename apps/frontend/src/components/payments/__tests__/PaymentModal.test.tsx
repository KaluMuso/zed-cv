import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentModal } from "../PaymentModal";

vi.mock("next/script", () => ({
  default: ({
    src,
    onLoad,
  }: {
    src: string;
    onLoad?: () => void;
  }) => (
    <div
      role="presentation"
      data-testid="lenco-script"
      data-src={src}
      onFocus={() => onLoad?.()}
    />
  ),
}));

const tiers = [
  { tier: "starter", name: "Starter", priceLabel: "K125/mo" },
  { tier: "professional", name: "Professional", priceLabel: "K250/mo" },
];

describe("PaymentModal", () => {
  it("does not render when closed", () => {
    render(
      <PaymentModal
        open={false}
        tiers={tiers}
        selectedTier={null}
        lencoReady
        lencoScriptUrl="https://pay.sandbox.lenco.co/js/v1/inline.js"
        payingTier={null}
        onSelectTier={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("payment-modal")).not.toBeInTheDocument();
  });

  it("renders tier options and mounts the Lenco script", () => {
    render(
      <PaymentModal
        open
        tiers={tiers}
        selectedTier="starter"
        lencoReady
        lencoScriptUrl="https://pay.sandbox.lenco.co/js/v1/inline.js"
        payingTier={null}
        onSelectTier={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("payment-modal")).toBeInTheDocument();
    expect(screen.getByTestId("tier-starter")).toBeInTheDocument();
    expect(screen.getByTestId("tier-professional")).toBeInTheDocument();
    const script = screen.getByTestId("lenco-script");
    expect(script).toHaveAttribute(
      "data-src",
      "https://pay.sandbox.lenco.co/js/v1/inline.js",
    );
  });

  it("calls onSelectTier when a tier is clicked", async () => {
    const user = userEvent.setup();
    const onSelectTier = vi.fn();
    render(
      <PaymentModal
        open
        tiers={tiers}
        selectedTier={null}
        lencoReady
        lencoScriptUrl="https://pay.sandbox.lenco.co/js/v1/inline.js"
        payingTier={null}
        onSelectTier={onSelectTier}
        onClose={vi.fn()}
      />,
    );
    await user.click(screen.getByTestId("tier-starter"));
    expect(onSelectTier).toHaveBeenCalledWith("starter");
  });

  it("disables tier buttons while Lenco is not ready", () => {
    render(
      <PaymentModal
        open
        tiers={tiers}
        selectedTier={null}
        lencoReady={false}
        lencoScriptUrl="https://pay.sandbox.lenco.co/js/v1/inline.js"
        payingTier={null}
        onSelectTier={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("tier-starter")).toBeDisabled();
  });
});
