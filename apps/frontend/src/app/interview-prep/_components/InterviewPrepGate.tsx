"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { profile as profileApi } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface InterviewPrepGateProps {
  children: ReactNode;
  nextPath: string;
}

export function InterviewPrepGate({ children, nextPath }: InterviewPrepGateProps) {
  const router = useRouter();
  const { token, isAuthenticated, isLoading } = useAuth();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !token) {
      router.replace(`/auth?next=${encodeURIComponent(nextPath)}`);
      return;
    }
    profileApi
      .get(token)
      .then((p) => setAllowed(p.subscription_tier === "super_standard"))
      .catch(() => setAllowed(false));
  }, [isAuthenticated, isLoading, token, router, nextPath]);

  if (isLoading || allowed === null) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center" style={{ color: "var(--muted)" }}>
        Loading…
      </div>
    );
  }

  if (!allowed) {
    return (
      <div className="max-w-lg mx-auto px-6 py-16 text-center">
        <h1 className="font-display text-3xl mb-3">Super Standard required</h1>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
          Bwana Interview (mock interviews and aptitude tests) is included on the
          Super Standard plan (K500/mo).
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/pricing">
            <Button variant="primary">Upgrade</Button>
          </Link>
          <Link href="/interview-prep">
            <Button variant="outline">Back</Button>
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
