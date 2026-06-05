"use client";

import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { PREMIUM_FEATURE_PURPLE } from "@/lib/premium-nav";
import {
  FEATURE_TIER_MAP,
  TIER_PRICE_KWACHA,
  tierAtLeast,
  tierDisplayName,
} from "@/lib/tier-features";
import { cn } from "@/lib/utils";

type JobDetailPremiumActionsProps = {
  subscriptionTier?: string | null;
  jobId: string;
  jobTitle: string;
  company: string;
  onCoverLetterClick: () => void;
};

function PremiumLockedButton({
  label,
  icon,
  feature,
  className,
}: {
  label: string;
  icon: "sparkle" | "file";
  feature: "cover_letter" | "tailor_cv";
  className?: string;
}) {
  const requiredTier = FEATURE_TIER_MAP[feature];
  const tierName = tierDisplayName(requiredTier);
  const price = TIER_PRICE_KWACHA[requiredTier];

  return (
    <Link
      href={`/pricing#${requiredTier}`}
      className={cn(
        "btn flex-1 sm:flex-none justify-center gap-1.5 text-xs sm:text-sm",
        className,
      )}
      title={`${label} requires ${tierName}`}
      data-testid={`job-detail-upgrade-${feature}`}
      style={{
        borderColor: `color-mix(in srgb, ${PREMIUM_FEATURE_PURPLE} 45%, var(--line))`,
        color: PREMIUM_FEATURE_PURPLE,
        background: `color-mix(in srgb, ${PREMIUM_FEATURE_PURPLE} 8%, var(--surface))`,
      }}
    >
      <Icon name={icon} size={14} />
      {label}
      <span className="opacity-80">· {tierName}</span>
      {price > 0 ? <span className="sr-only">K{price} per month</span> : null}
    </Link>
  );
}

/**
 * Cover letter + tailored CV on job detail — Professional+ only.
 * Free and Starter see purple upgrade links instead of live actions.
 */
export function JobDetailPremiumActions({
  subscriptionTier,
  jobId,
  jobTitle,
  company,
  onCoverLetterClick,
}: JobDetailPremiumActionsProps) {
  const requiredTier = FEATURE_TIER_MAP.cover_letter;
  const unlocked = tierAtLeast(subscriptionTier, requiredTier);

  if (!unlocked) {
    return (
      <>
        <PremiumLockedButton
          label="Generate cover letter"
          icon="sparkle"
          feature="cover_letter"
        />
        <PremiumLockedButton label="Tailored CV" icon="file" feature="tailor_cv" />
      </>
    );
  }

  return (
    <>
      <button
        type="button"
        className="btn btn-outline flex-1 sm:flex-none justify-center gap-1.5"
        onClick={onCoverLetterClick}
        data-testid="job-detail-cover-letter"
      >
        <Icon name="sparkle" size={14} /> Generate cover letter
      </button>
      <Link
        href={`/profile/cv-builder?jobId=${encodeURIComponent(jobId)}&jobTitle=${encodeURIComponent(jobTitle)}&company=${encodeURIComponent(company)}`}
        className="btn btn-ghost flex-1 sm:flex-none justify-center gap-1.5"
        data-testid="job-detail-tailored-cv"
      >
        <Icon name="file" size={14} /> Tailored CV
      </Link>
    </>
  );
}
