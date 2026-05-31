"use client";

import Script from "next/script";
import { Button } from "@/components/ui/button";

export interface PaymentTierOption {
  tier: string;
  name: string;
  priceLabel: string;
  highlight?: boolean;
}

export interface PaymentModalProps {
  open: boolean;
  tiers: PaymentTierOption[];
  selectedTier: string | null;
  lencoReady: boolean;
  lencoScriptUrl: string;
  payingTier: string | null;
  onSelectTier: (tier: string) => void;
  onClose: () => void;
  onLencoScriptLoad?: () => void;
  onLencoScriptError?: () => void;
}

export function PaymentModal({
  open,
  tiers,
  selectedTier,
  lencoReady,
  lencoScriptUrl,
  payingTier,
  onSelectTier,
  onClose,
  onLencoScriptLoad,
  onLencoScriptError,
}: PaymentModalProps) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="payment-modal"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        aria-label="Close payment modal"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-lg rounded-xl card p-6 shadow-lg">
        <Script
          src={lencoScriptUrl}
          strategy="afterInteractive"
          onLoad={onLencoScriptLoad}
          onError={onLencoScriptError}
          data-testid="lenco-script"
        />
        <h2 id="payment-modal-title" className="font-display text-2xl mb-2">
          Choose a plan
        </h2>
        <p className="text-sm text-muted-foreground mb-6">
          {lencoReady
            ? "Secure Lenco checkout — MTN MoMo, Airtel Money, or card."
            : "Loading payment widget…"}
        </p>
        <div className="flex flex-col gap-3">
          {tiers.map((plan) => {
            const isSelected = selectedTier === plan.tier;
            const isPaying = payingTier === plan.tier;
            return (
              <button
                key={plan.tier}
                type="button"
                className={`card p-4 text-left w-full ${plan.highlight ? "ring-2 ring-copper-500" : ""}`}
                aria-pressed={isSelected}
                disabled={!lencoReady || isPaying}
                onClick={() => onSelectTier(plan.tier)}
                data-testid={`tier-${plan.tier}`}
              >
                <div className="flex justify-between items-center gap-2">
                  <span className="font-medium">{plan.name}</span>
                  <span className="font-mono text-sm">{plan.priceLabel}</span>
                </div>
                {isPaying ? (
                  <span className="text-xs text-muted-foreground mt-1 block">
                    Opening checkout…
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        <Button type="button" variant="ghost" className="mt-6 w-full" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
