"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  matches as matchesApi,
  savedJobs,
  profile as profileApi,
  subscription as subscriptionApi,
  preferencesApi,
  type MatchData,
  type Subscription,
  type UserProfile,
  type JobPreferences,
} from "@/lib/api";
import { UserDashboard } from "@/components/dashboard/UserDashboard";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import { computeProfileCompleteness } from "@/lib/profileCompleteness";
import { DashboardSkeleton } from "@/components/shared/skeletons/PageSkeletons";

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
  const [profileCompleteness, setProfileCompleteness] = useState<{
    percent: number;
    hints: string[];
  } | null>(null);
  const [applicationsCount, setApplicationsCount] = useState(0);
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
      savedJobs.list(token).catch(() => ({ jobs: [], applications: [] })),
      subscriptionApi.get(token).catch(() => null),
      preferencesApi.get(token).catch(() => null),
    ])
      .then(([prof, matchRes, savedRes, sub, prefs]) => {
        if (cancelled) return;
        setUserName(prof.full_name ?? undefined);
        setSubscriptionTier(prof.subscription_tier);
        setSubscription(sub);
        const completeness = computeProfileCompleteness({
          profile: prof as UserProfile,
          preferences: prefs as JobPreferences | null,
        });
        setProfileCompleteness({
          percent: completeness.percent,
          hints: completeness.items.filter((i) => !i.complete).map((i) => i.hint).slice(0, 4),
        });
        const sorted = [...matchRes.matches].sort((a, b) => b.score - a.score);
        setTopMatches(sorted.slice(0, 3));
        setSavedCount(savedRes.jobs.length);
        setApplicationsCount(
          savedRes.applications?.length ?? savedRes.jobs.length,
        );
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
    return <DashboardSkeleton />;
  }

  return (
    <UserDashboard
      userName={userName}
      subscription={subscription}
      subscriptionTier={subscriptionTier}
      subscriptionTierLabel={TIER_NAV_LABELS[subscriptionTier] ?? subscriptionTier}
      profileCompleteness={profileCompleteness ?? undefined}
      applicationsCount={applicationsCount}
      liveData={{
        totalMatches: totalMatchCount,
        savedJobs: savedCount,
        avgScore,
        topMatches,
      }}
    />
  );
}
