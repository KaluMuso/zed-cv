"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { admin, profile as profileApi } from "@/lib/api";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [ok, setOk] = useState(false);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!isAuthenticated || !token) {
      router.replace("/auth?next=/admin");
      return;
    }
    profileApi
      .get(token)
      .then((p) => {
        if (p.role === "superadmin" || p.role === "admin") {
          setOk(true);
          admin
            .stats(token)
            .then((stats) => setPendingReviewCount(stats.pending_review_count ?? 0))
            .catch(() => setPendingReviewCount(0));
        } else {
          router.replace("/");
        }
      })
      .catch(() => {
        router.replace("/");
      });
  }, [authLoading, isAuthenticated, token, router]);

  if (authLoading || !ok) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-sm text-muted-foreground">Checking access…</div>
    );
  }
  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-8">
      {pendingReviewCount > 0 && (
        <Link
          href="/admin/jobs/review"
          className="mb-4 flex items-center justify-between rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900"
        >
          <span>{pendingReviewCount} jobs need review</span>
          <span aria-hidden="true">&rarr;</span>
        </Link>
      )}
      {children}
    </div>
  );
}
