"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { UserProfile } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { ManualCvWizard } from "@/features/manual-cv-wizard/ManualCvWizard";

/**
 * Profile "CV Generator" tab — manual wizard when no CV uploaded;
 * paid users with an uploaded CV go to the tailored builder.
 */
export function GeneratorTab({
  token,
  profileData,
  onCvCreated,
}: {
  token: string;
  profileData: UserProfile;
  onCvCreated?: () => void;
}) {
  const router = useRouter();
  const tier = profileData.subscription_tier;
  const tierAllowed =
    tier === "starter" || tier === "professional" || tier === "super_standard";
  const shouldRedirect = profileData.cv_uploaded && tierAllowed;

  useEffect(() => {
    if (shouldRedirect) {
      router.replace("/profile/cv-builder");
    }
  }, [shouldRedirect, router]);

  if (!profileData.cv_uploaded) {
    return (
      <div className="card p-4 sm:p-6">
        <ManualCvWizard token={token} onCvCreated={onCvCreated} />
      </div>
    );
  }

  if (!tierAllowed) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">Tailored CV</div>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          Tailored CVs are included on Starter plans and above.
        </p>
        <Link href="/pricing" className="btn btn-accent btn-sm inline-flex gap-1.5">
          <Icon name="zap" size={14} /> View plans
        </Link>
      </div>
    );
  }

  return (
    <p className="text-sm py-8 text-center" style={{ color: "var(--muted)" }}>
      Opening tailored CV builder…
    </p>
  );
}
