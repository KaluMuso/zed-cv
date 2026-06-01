"use client";

import type { ReactNode } from "react";

import { useUserTier } from "@/hooks/useUserTier";
import {
  FEATURE_TIER_MAP,
  tierAtLeast,
  type TierFeature,
} from "@/lib/tier-features";
import { UpgradeButton } from "@/components/shared/UpgradeButton";

type TierGateProps = {
  feature: TierFeature;
  children: ReactNode;
  /** When locked, render this instead of the default UpgradeButton. */
  fallback?: ReactNode;
  upgradeClassName?: string;
};

export function TierGate({
  feature,
  children,
  fallback,
  upgradeClassName,
}: TierGateProps) {
  const { tier, loading } = useUserTier();
  const requiredTier = FEATURE_TIER_MAP[feature];

  if (loading) {
    return (
      <span
        className="inline-block h-9 w-40 rounded-md bg-muted/40 animate-pulse"
        aria-hidden
      />
    );
  }

  if (tierAtLeast(tier, requiredTier)) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  return (
    <UpgradeButton
      feature={feature}
      requiredTier={requiredTier}
      className={upgradeClassName}
    />
  );
}
