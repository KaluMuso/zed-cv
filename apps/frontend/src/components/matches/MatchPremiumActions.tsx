"use client";

import { useUserTier } from "@/hooks/useUserTier";
import { FEATURE_TIER_MAP, tierAtLeast } from "@/lib/tier-features";
import { UpgradeButton } from "@/components/shared/UpgradeButton";
import { btnClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

type MatchPremiumActionsProps = {
  onTailorCvClick?: () => void;
  onCoverLetterClick?: () => void;
};

/**
 * Tailor CV + cover letter on match cards. When both are tier-gated, show one
 * upgrade CTA (both require Professional) to avoid duplicate overlapping links.
 */
export function MatchPremiumActions({
  onTailorCvClick,
  onCoverLetterClick,
}: MatchPremiumActionsProps) {
  const { tier, loading } = useUserTier();
  const requiredTier = FEATURE_TIER_MAP.tailor_cv;
  const unlocked = tierAtLeast(tier, requiredTier);

  if (loading) {
    return (
      <div
        className="h-9 w-full rounded-md bg-muted/40 animate-pulse"
        aria-hidden
      />
    );
  }

  if (!unlocked) {
    return (
      <UpgradeButton
        feature="tailor_cv"
        requiredTier={requiredTier}
        className="w-full"
      />
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
      <button
        type="button"
        className={cn(btnClass("accent", "sm"), "w-full text-xs")}
        onClick={onTailorCvClick}
        data-testid="match-tailor-cv"
      >
        Tailor my CV
      </button>
      <button
        type="button"
        className={cn(btnClass("outline", "sm"), "w-full text-xs")}
        onClick={onCoverLetterClick}
        data-testid="match-cover-letter"
      >
        Cover letter
      </button>
    </div>
  );
}
