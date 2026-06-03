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
  type MatchListResponse,
  type Subscription,
  type UserProfile,
  type JobPreferences,
} from "@/lib/api";
import { UserDashboard } from "@/components/dashboard/UserDashboard";
import type { ApplicationFunnel } from "@/components/dashboard/DashboardInsights";
import type { SavedJobApplication } from "@/lib/api";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import { computeProfileCompleteness } from "@/lib/profileCompleteness";
import { DashboardSkeleton } from "@/components/shared/skeletons/PageSkeletons";
import {
  buildDashboardMatchStats,
  DASHBOARD_MATCHES_FETCH_LIMIT,
  type DashboardQuotaDisplay,
} from "@/lib/dashboard-stats";

function buildApplicationFunnel(
  applications: SavedJobApplication[] | undefined,
): ApplicationFunnel {
  const funnel: ApplicationFunnel = {
    saved: 0,
    applied: 0,
    interviewing: 0,
    offered: 0,
    closed: 0,
  };
  for (const row of applications ?? []) {
    switch (row.application_status) {
      case "saved":
        funnel.saved += 1;
        break;
      case "applied":
        funnel.applied += 1;
        break;
      case "interviewing":
        funnel.interviewing += 1;
        break;
      case "offered":
        funnel.offered += 1;
        break;
      case "closed_won":
      case "closed_lost":
        funnel.closed += 1;
        break;
      default:
        break;
    }
  }
  return funnel;
}

const EMPTY_MATCH_LIST: MatchListResponse = {
  matches: [],
  remaining_quota: 0,
};

export function DashboardPageClient() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [userName, setUserName] = useState<string | undefined>();
  const [topMatches, setTopMatches] = useState<MatchData[]>([]);
  const [savedCount, setSavedCount] = useState(0);
  const [avgScore, setAvgScore] = useState<number | null>(null);
  const [totalMatchCount, setTotalMatchCount] = useState(0);
  const [matchQuota, setMatchQuota] = useState<DashboardQuotaDisplay | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [subscriptionTier, setSubscriptionTier] = useState("free");
  const [profileCompleteness, setProfileCompleteness] = useState<{
    percent: number;
    hints: string[];
  } | null>(null);
  const [applicationsCount, setApplicationsCount] = useState(0);
  const [applicationFunnel, setApplicationFunnel] = useState<ApplicationFunnel | undefined>();
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
      matchesApi
        .get(token, { limit: DASHBOARD_MATCHES_FETCH_LIMIT })
        .catch(() => EMPTY_MATCH_LIST),
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
        const stats = buildDashboardMatchStats(matchRes.matches, matchRes, sub);
        setTopMatches(stats.topMatches);
        setTotalMatchCount(stats.poolCount);
        setAvgScore(stats.avgScore);
        setMatchQuota(stats.quota);
        setSavedCount(savedRes.jobs.length);
        const apps = savedRes.applications ?? [];
        setApplicationsCount(apps.length > 0 ? apps.length : savedRes.jobs.length);
        setApplicationFunnel(buildApplicationFunnel(savedRes.applications));
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
      applicationFunnel={applicationFunnel}
      matchQuota={matchQuota ?? undefined}
      liveData={{
        totalMatches: totalMatchCount,
        savedJobs: savedCount,
        avgScore,
        topMatches,
      }}
    />
  );
}
