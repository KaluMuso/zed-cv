"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { UserProfile } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

/**
 * Profile "CV Generator" tab — routes paid users to the unified tailored CV
 * builder at /profile/cv-builder (PDF §4).
 */
export function GeneratorTab({
  profileData,
}: {
  token: string;
  profileData: UserProfile;
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
      <div className="card p-6">
        <div className="eyebrow mb-2">CV generator</div>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Upload your CV first — the generator tailors your existing CV to a target role.
        </p>
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
