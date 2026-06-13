"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { boosters, profile } from "@/lib/api";
import { notify } from "@/lib/toast";
import { getLencoPublicKey, getLencoScriptUrl, isLencoReady, lencoPhone, openLencoCheckout, setLencoMerchantLabel } from "@/lib/lenco";
import Script from "next/script";
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

  return (
    <>
      <Script src={getLencoScriptUrl()} strategy="afterInteractive" />
      {unlocked ? (
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
      ) : (
        <>
          <PremiumLockedButton
            label="Generate cover letter"
            icon="sparkle"
            feature="cover_letter"
          />
          <PremiumLockedButton label="Tailored CV" icon="file" feature="tailor_cv" />
        </>
      )}
      
      <div className="w-full mt-2 pt-4 border-t border-[var(--line)]">
        <h4 className="text-sm font-semibold mb-3 text-[var(--ink)]">Or pay per use (Boosters)</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <BoosterCard 
            sku="tailored_cv" 
            title="Tailored CV" 
            description="AI-tailor your CV for this exact job in 60 seconds." 
            priceKwacha={20} 
            icon="file"
          />
          <BoosterCard 
            sku="cover_letter" 
            title="Cover Letter" 
            description="AI-write a cover letter targeted at this role." 
            priceKwacha={15} 
            icon="sparkle"
          />
          <BoosterCard 
            sku="interview_prep" 
            title="Interview Prep" 
            description="Get 10 likely interview questions + model answers." 
            priceKwacha={40} 
            icon="messageCircle"
          />
        </div>
      </div>
    </>
  );
}

function BoosterCard({ sku, title, description, priceKwacha, icon }: { sku: string, title: string, description: string, priceKwacha: number, icon: string }) {
  const { token, user, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);

  const handlePurchase = async () => {
    if (!isAuthenticated || !token || !user) {
      notify.error("Please sign in to purchase boosters.");
      return;
    }

    if (!isLencoReady()) {
      notify.error("Payment widget is loading — please wait a moment and try again.");
      return;
    }

    setLoading(true);
    try {
      const response = await boosters.purchase(token, sku);
      
      let prof = null;
      try {
        prof = await profile.get(token);
      } catch (err) {
        // ignore
      }

      const email = prof?.email?.trim() || `payments+${user.id.slice(0, 8)}@zedapply.com`;
      const full = (prof?.full_name || "Zed CV User").trim();
      const parts = full.split(/\s+/).filter(Boolean);
      const firstName = parts[0] || "Zed";
      const lastName = parts.length > 1 ? parts.slice(1).join(" ") : firstName;

      setLencoMerchantLabel("ZedApply Boosters");

      openLencoCheckout({
        key: getLencoPublicKey() || "",
        label: "ZedApply Boosters",
        reference: response.reference,
        email,
        amount: response.amount_ngwee / 100,
        currency: "ZMW",
        channels: ["card", "mobile-money"],
        customer: {
          firstName,
          lastName,
          phone: lencoPhone(prof?.phone),
        },
        onSuccess: async () => {
          notify.success("Booster purchased successfully!");
          setLoading(false);
        },
        onClose: () => {
          notify.info("Payment cancelled");
          setLoading(false);
        },
        onConfirmationPending: () => {
          notify.info("Payment processing — your booster will be active shortly.");
        },
      });
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not initiate purchase");
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col p-4 rounded-xl border bg-[var(--surface)] shadow-sm" style={{ borderColor: "var(--line)" }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="p-1.5 rounded-md" style={{ background: "color-mix(in srgb, var(--copper-500) 10%, transparent)", color: "var(--copper-600)" }}>
          <Icon name={icon as any} size={16} />
        </span>
        <h5 className="font-semibold text-sm">{title}</h5>
      </div>
      <p className="text-xs text-[var(--muted)] mb-4 flex-1">{description}</p>
      <div className="flex items-center justify-between mt-auto">
        <span className="font-display font-medium">K{priceKwacha}</span>
        <button 
          onClick={handlePurchase}
          disabled={loading}
          className="btn btn-primary btn-sm px-4 py-1.5 h-auto text-xs"
        >
          {loading ? "..." : "Get Booster"}
        </button>
      </div>
    </div>
  );
}
