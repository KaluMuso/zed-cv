"use client";

import { useUserTier } from "@/hooks/useUserTier";
import { FEATURE_TIER_MAP, tierAtLeast } from "@/lib/tier-features";
import { UpgradeButton } from "@/components/shared/UpgradeButton";
import { btnClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

type MatchPremiumActionsProps = {
  onTailorCvClick?: () => void;
  onCoverLetterClick?: () => void;
  onInterviewPrepClick?: () => void;
};

/**
 * Tailor CV + cover letter on match cards (Professional+). Interview prep is
 * Super Standard — show an upgrade CTA on Professional, full button on Super Standard.
 */
export function MatchPremiumActions({
  onTailorCvClick,
  onCoverLetterClick,
  onInterviewPrepClick,
}: MatchPremiumActionsProps) {
  const { tier, loading } = useUserTier();
  const requiredTier = FEATURE_TIER_MAP.tailor_cv;
  const prepTier = FEATURE_TIER_MAP.unlock_prep;
  const unlocked = tierAtLeast(tier, requiredTier);
  const prepUnlocked = tierAtLeast(tier, prepTier);

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

  const showPrep = Boolean(onInterviewPrepClick);

  return (
    <div
      className={cn(
        "grid gap-2 w-full",
        showPrep ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-1 sm:grid-cols-2",
      )}
    >
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
      {showPrep &&
        (prepUnlocked ? (
          <button
            type="button"
            className={cn(btnClass("outline", "sm"), "w-full text-xs")}
            onClick={onInterviewPrepClick}
            data-testid="match-interview-prep"
          >
            Interview prep
          </button>
        ) : (
          <UpgradeButton
            feature="unlock_prep"
            requiredTier={prepTier}
            className="w-full text-xs"
          />
        ))}
    </div>
  );
}
