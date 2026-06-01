"use client";

import Link from "next/link";
import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { TierGate } from "@/components/shared/TierGate";
import { FEATURE_TIER_MAP, tierDisplayName } from "@/lib/tier-features";

interface InterviewPrepGateProps {
  children: ReactNode;
  nextPath: string;
}

export function InterviewPrepGate({ children, nextPath }: InterviewPrepGateProps) {
  const router = useRouter();
  const { token, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !token) {
      router.replace(`/auth?next=${encodeURIComponent(nextPath)}`);
    }
  }, [isAuthenticated, isLoading, token, router, nextPath]);

  if (isLoading || !isAuthenticated || !token) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center" style={{ color: "var(--muted)" }}>
        Loading…
      </div>
    );
  }

  const required = FEATURE_TIER_MAP.unlock_prep;

  return (
    <TierGate
      feature="unlock_prep"
      fallback={
        <div className="max-w-lg mx-auto px-6 py-16 text-center">
          <h1 className="font-display text-3xl mb-3">
            Upgrade to {tierDisplayName(required)}
          </h1>
          <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
            Interview prep is included on {tierDisplayName(required)}. Upgrade for mock
            interviews, aptitude practice, and tailored prep briefs.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href={`/pricing#${required}`}>
              <Button variant="primary">Upgrade for this feature</Button>
            </Link>
            <Link href="/interview-prep">
              <Button variant="outline">Back</Button>
            </Link>
          </div>
        </div>
      }
    >
      {children}
    </TierGate>
  );
}
