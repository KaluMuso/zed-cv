"use client";

import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import { PREMIUM_FEATURE_PURPLE } from "@/lib/premium-nav";
import {
  FEATURE_TIER_MAP,
  TIER_PRICE_KWACHA,
  tierDisplayName,
} from "@/lib/tier-features";
import { cn } from "@/lib/utils";

type MatchBreakdownUpgradePromptProps = {
  className?: string;
  compact?: boolean;
};

/**
 * Upgrade CTA when free-tier users open match breakdown surfaces.
 * Purple accent matches Interview Prep premium nav styling.
 */
export function MatchBreakdownUpgradePrompt({
  className,
  compact = false,
}: MatchBreakdownUpgradePromptProps) {
  const requiredTier = FEATURE_TIER_MAP.match_score_breakdown;
  const tierName = tierDisplayName(requiredTier);
  const price = TIER_PRICE_KWACHA[requiredTier];

  return (
    <div
      className={cn("rounded-xl text-center", compact ? "p-4" : "p-5 sm:p-6", className)}
      style={{
        background: `color-mix(in srgb, ${PREMIUM_FEATURE_PURPLE} 10%, var(--surface))`,
        border: `1px solid color-mix(in srgb, ${PREMIUM_FEATURE_PURPLE} 32%, var(--line))`,
      }}
      data-testid="match-breakdown-upgrade"
    >
      <div
        className="inline-flex items-center justify-center w-10 h-10 rounded-full mb-3"
        style={{
          background: `color-mix(in srgb, ${PREMIUM_FEATURE_PURPLE} 18%, transparent)`,
          color: PREMIUM_FEATURE_PURPLE,
        }}
        aria-hidden
      >
        <Icon name="shield" size={18} />
      </div>

      <p
        className="text-[10px] font-bold uppercase tracking-widest mb-2"
        style={{ color: PREMIUM_FEATURE_PURPLE }}
      >
        Starter plan and above
      </p>

      <h3
        className={cn("font-display mb-2", compact ? "text-lg" : "text-xl")}
        style={{ letterSpacing: "-0.01em" }}
      >
        Unlock the full match breakdown
      </h3>

      <p className="text-sm leading-relaxed mb-1" style={{ color: "var(--muted)" }}>
        Score breakdowns, AI explanations, and skill gap analysis are included on{" "}
        <strong style={{ color: "var(--ink)" }}>{tierName}</strong> and higher paid
        plans.
      </p>

      <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
        Your Free plan shows only the overall match score.
      </p>

      <Link href={`/pricing#${requiredTier}`} className="inline-flex">
        <Button
          type="button"
          size={compact ? "sm" : "default"}
          className="gap-1.5"
          style={{
            background: PREMIUM_FEATURE_PURPLE,
            borderColor: PREMIUM_FEATURE_PURPLE,
            color: "#fff",
          }}
        >
          Upgrade to {tierName}
          {price > 0 ? ` · K${price}/mo` : ""}
        </Button>
      </Link>
    </div>
  );
}
