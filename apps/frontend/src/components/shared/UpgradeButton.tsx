"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  FEATURE_LABELS,
  TIER_PRICE_KWACHA,
  tierDisplayName,
  type TierFeature,
} from "@/lib/tier-features";
import type { SubscriptionTier } from "@/lib/tier-features";
import { cn } from "@/lib/utils";

type UpgradeButtonProps = {
  feature: TierFeature;
  requiredTier: SubscriptionTier;
  className?: string;
  size?: "sm" | "default";
  variant?: "outline" | "ghost" | "accent";
};

export function UpgradeButton({
  feature,
  requiredTier,
  className,
  size = "sm",
  variant = "outline",
}: UpgradeButtonProps) {
  const price = TIER_PRICE_KWACHA[requiredTier];
  const tierName = tierDisplayName(requiredTier);
  const label = FEATURE_LABELS[feature];

  return (
    <Link
      href={`/pricing#${requiredTier}`}
      className={cn("inline-flex w-full sm:w-auto", className)}
      title={`${label} requires ${tierName}`}
      data-testid={`upgrade-${feature}`}
    >
      <Button
        type="button"
        variant={variant}
        size={size}
        className="w-full pointer-events-none opacity-90"
        disabled
        aria-disabled
      >
        Upgrade to {tierName}
        {price > 0 ? ` · K${price}/mo` : ""}
      </Button>
    </Link>
  );
}
