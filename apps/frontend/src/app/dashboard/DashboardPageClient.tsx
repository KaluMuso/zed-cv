"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  matches as matchesApi,
  savedJobs,
  profile as profileApi,
  subscription as subscriptionApi,
  type MatchData,
  type Subscription,
} from "@/lib/api";
import { UserDashboard } from "@/components/dashboard/UserDashboard";
import { TIER_NAV_LABELS } from "@/lib/tier-display";

export function DashboardPageClient() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [userName, setUserName] = useState<string | undefined>();
  const [topMatches, setTopMatches] = useState<MatchData[]>([]);
  const [savedCount, setSavedCount] = useState(0);
  const [avgScore, setAvgScore] = useState<number | null>(null);
  const [totalMatchCount, setTotalMatchCount] = useState(0);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [subscriptionTier, setSubscriptionTier] = useState("free");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.replace("/auth?next=/dashboard");
      return;
    }
    let cancelled = false;
    Promise.all([
      profileApi.get(token),
      matchesApi.get(token).catch(() => ({ matches: [] as MatchData[] })),
      savedJobs.list(token).catch(() => ({ jobs: [] })),
      subscriptionApi.get(token).catch(() => null),
    ])
      .then(([prof, matchRes, savedRes, sub]) => {
        if (cancelled) return;
        setUserName(prof.full_name ?? undefined);
        setSubscriptionTier(prof.subscription_tier);
        setSubscription(sub);
        const sorted = [...matchRes.matches].sort((a, b) => b.score - a.score);
        setTopMatches(sorted.slice(0, 3));
        setSavedCount(savedRes.jobs.length);
        setTotalMatchCount(sorted.length);
        if (sorted.length > 0) {
          const avg = Math.round(
            sorted.reduce((sum, m) => sum + m.score, 0) / sorted.length,
          );
          setAvgScore(avg);
        } else {
          setAvgScore(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, isAuthenticated, authLoading, router]);

  if (authLoading || loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 py-8">
        <div className="skeleton h-10 w-64" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <UserDashboard
      userName={userName}
      subscription={subscription}
      subscriptionTier={subscriptionTier}
      subscriptionTierLabel={TIER_NAV_LABELS[subscriptionTier] ?? subscriptionTier}
      liveData={{
        totalMatches: totalMatchCount,
        savedJobs: savedCount,
        avgScore,
        topMatches,
      }}
    />
  );
}
