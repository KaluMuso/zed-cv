"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  profile as profileApi,
  subscription as subscriptionApi,
  ApiError,
  type Subscription,
  type UserProfile,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { StepProgress } from "@/components/shared/StepProgress";

import { CvSkillsTab } from "./_tabs/CvSkillsTab";
import { AnalysisTab } from "./_tabs/AnalysisTab";
import { GeneratorTab } from "./_tabs/GeneratorTab";
import { ProfileReferralCard } from "./_tabs/ProfileReferralCard";

type Tab = "cv" | "analysis" | "generator";

const TABS: { key: Tab; label: string }[] = [
  { key: "cv", label: "CV & Skills" },
  { key: "analysis", label: "CV Analysis" },
  { key: "generator", label: "CV Generator" },
];

// Mapping from URL `?tab=` slug (kebab-case, user-facing) to internal Tab key.
// The navbar links to /profile?tab=cv-generator etc.; without this map the page
// silently fell back to the default tab and the URL became cosmetic only.
const TAB_FROM_SLUG: Record<string, Tab> = {
  "cv": "cv",
  "cv-skills": "cv",
  "cv-analysis": "analysis",
  "analysis": "analysis",
  "cv-generator": "generator",
  "generator": "generator",
  preferences: "cv",
};

const SLUG_FROM_TAB: Record<Tab, string> = {
  cv: "cv-skills",
  analysis: "cv-analysis",
  generator: "cv-generator",
};

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter (K125/mo)",
  professional: "Professional (K250/mo)",
  super_standard: "Super Standard (K500/mo)",
};

function formatWelcomeEnd(iso: string | null | undefined): string {
  if (!iso) return "soon";
  try {
    return new Date(iso).toLocaleDateString("en-ZM", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "soon";
  }
}

export default function ProfilePageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const [profileData, setProfileData] = useState<UserProfile | null>(null);
  const [subscriptionData, setSubscriptionData] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize the tab from the `?tab=` URL slug so dropdown links like
  // /profile?tab=cv-generator actually open the right tab. Falls back to "cv"
  // for unknown / missing slugs.
  const tabSlug = searchParams.get("tab") ?? "cv";
  const initialTab: Tab = TAB_FROM_SLUG[tabSlug] ?? "cv";
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);

  // Legacy: job preferences moved to /settings/job-preferences
  useEffect(() => {
    const slug = searchParams.get("tab");
    if (slug === "preferences") {
      router.replace("/settings/job-preferences");
    }
  }, [searchParams, router]);

  // Keep state in sync when the URL changes (e.g. user navigates from nav
  // dropdown to a different tab via Link). Without this, the second click
  // is a no-op because the page is already mounted.
  useEffect(() => {
    const slug = searchParams.get("tab") ?? "cv";
    if (slug === "preferences") return;
    const tab = TAB_FROM_SLUG[slug];
    if (tab && tab !== activeTab) setActiveTab(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // When the user clicks a tab, push the slug to the URL so the state is
  // shareable and back-button-able. router.replace (not push) so the tab
  // history doesn't pollute back navigation.
  const onTabChange = (tab: Tab) => {
    setActiveTab(tab);
    const slug = SLUG_FROM_TAB[tab];
    router.replace(`/profile?tab=${slug}`, { scroll: false });
  };

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth?next=/profile");
      return;
    }
    Promise.all([
      profileApi.get(token),
      subscriptionApi.get(token).catch(() => null),
    ])
      .then(([profileRes, subRes]) => {
        setProfileData(profileRes);
        setSubscriptionData(subRes);
      })
      .catch((err) => {
        // 401 = stale JWT (typical: 24h expiry while user was away).
        // Clear and bounce to /auth so the user has a recovery path
        // instead of staring at "Could not load profile" forever.
        if (err instanceof ApiError && err.status === 401) {
          logout();
          router.replace("/auth?next=/profile");
          return;
        }
        setProfileData(null);
      })
      .finally(() => setLoading(false));
  }, [token, isAuthenticated, authLoading, router, logout]);

  const refresh = () => {
    if (!token) return;
    profileApi.get(token).then(setProfileData).catch(() => {});
    subscriptionApi.get(token).then(setSubscriptionData).catch(() => setSubscriptionData(null));
  };

  if (loading || authLoading) {
    // Skeleton mirrors the loaded layout: header card with avatar + name lines
    // + tier tag + completion ring, then tab strip, then 2-col body (tab
    // content on the left, plan + account sidebar on the right). Same outer
    // padding as the loaded page so there's no layout shift on resolve.
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
        <div className="card p-6 md:p-8 mb-8">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex items-center gap-5 flex-1">
              <div
                className="skeleton rounded-full shrink-0"
                style={{ width: 72, height: 72 }}
              />
              <div className="min-w-0 flex-1">
                <div className="skeleton h-8 w-56 mb-2" />
                <div className="skeleton h-4 w-32 mb-3" />
                <div className="flex items-center gap-2">
                  <div className="skeleton h-6 w-20 rounded-full" />
                  <div className="skeleton h-6 w-32 rounded-full" />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div
                className="skeleton rounded-full shrink-0"
                style={{ width: 80, height: 80 }}
              />
              <div>
                <div className="skeleton h-4 w-32 mb-2" />
                <div className="skeleton h-3 w-44" />
              </div>
            </div>
          </div>
        </div>

        <div
          className="flex gap-6 mb-8"
          style={{ borderBottom: "1px solid var(--line)" }}
        >
          <div className="skeleton h-4 w-20 mb-3" />
          <div className="skeleton h-4 w-24 mb-3" />
          <div className="skeleton h-4 w-24 mb-3" />
          <div className="skeleton h-4 w-20 mb-3" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6">
              <div className="skeleton h-3 w-24 mb-4" />
              <div className="skeleton h-32 w-full mb-3" />
              <div className="skeleton h-4 w-5/6 mb-2" />
              <div className="skeleton h-4 w-4/6" />
            </div>
          </div>
          <div className="space-y-6">
            <div className="card p-6">
              <div className="skeleton h-3 w-20 mb-3" />
              <div className="skeleton h-7 w-40 mb-3" />
              <div className="skeleton h-4 w-full mb-2" />
              <div className="skeleton h-4 w-3/4 mb-4" />
              <div className="skeleton h-9 w-full rounded-md" />
            </div>
            <div className="card p-6">
              <div className="skeleton h-3 w-20 mb-4" />
              <div className="space-y-3">
                <div>
                  <div className="skeleton h-3 w-12 mb-1" />
                  <div className="skeleton h-4 w-32" />
                </div>
                <div>
                  <div className="skeleton h-3 w-12 mb-1" />
                  <div className="skeleton h-4 w-28" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!profileData || !token) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-20 text-center">
        <p style={{ color: "var(--muted)" }}>Could not load profile.</p>
      </div>
    );
  }

  // Defensive .length reads — backend has occasionally returned profile
  // payloads missing `skills` entirely, which crashed the page with
  // "Cannot read properties of undefined (reading 'length')". Treat absent
  // skills as empty so the page renders gracefully.
  const skillsList = profileData.skills ?? [];
  const fields = [
    !!profileData.full_name,
    !!profileData.phone,
    profileData.cv_uploaded,
    skillsList.length > 0,
  ];
  const completeness = Math.round(
    (fields.filter(Boolean).length / fields.length) * 100
  );
  const onboardingStep = !profileData.cv_uploaded
    ? 1
    : skillsList.length === 0
      ? 2
      : 3;

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      {!profileData.cv_uploaded || skillsList.length === 0 ? (
        <StepProgress
          current={onboardingStep}
          total={3}
          labels={["Upload CV", "Review skills", "Job preferences"]}
          className="mb-6 max-w-md"
        />
      ) : null}
      <div
        className="card p-6 md:p-8 mb-8 overflow-hidden"
        style={{
          background:
            "linear-gradient(135deg, var(--green-800) 0%, var(--green-700) 55%, var(--green-600) 100%)",
          borderColor: "transparent",
        }}
      >
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          <div className="flex items-center gap-5 flex-1">
            <Avatar name={profileData.full_name || "User"} size={72} />
            <div>
              <h1
                className="font-display text-3xl"
                style={{ letterSpacing: "-0.01em", color: "var(--green-50)" }}
              >
                {profileData.full_name || "Your Profile"}
              </h1>
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>
                {profileData.phone}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="tag tag-green">
                  <Icon name="check" size={10} /> Verified
                </span>
                <span className="tag tag-copper">
                  {TIER_LABELS[profileData.subscription_tier] || profileData.subscription_tier}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <svg width={80} height={80} className="-rotate-90">
                <circle cx={40} cy={40} r={34} fill="none" className="score-ring-track" strokeWidth={5} />
                <circle
                  cx={40}
                  cy={40}
                  r={34}
                  fill="none"
                  stroke="var(--copper-500)"
                  strokeWidth={5}
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 34}
                  strokeDashoffset={2 * Math.PI * 34 - (completeness / 100) * 2 * Math.PI * 34}
                  style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.2,0.7,0.2,1)" }}
                />
              </svg>
              <span
                className="absolute inset-0 flex items-center justify-center font-display text-lg font-bold"
                style={{ color: "var(--copper-500)" }}
              >
                {completeness}%
              </span>
            </div>
            <div>
              <div className="text-sm font-medium">Profile complete</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {completeness < 100 ? "Add more details to improve matches" : "Looking great!"}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        className="flex gap-6 mb-8 overflow-x-auto"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className="pb-3 text-sm font-medium relative shrink-0"
            style={{
              color: activeTab === tab.key ? "var(--ink)" : "var(--muted)",
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            {tab.label}
            {activeTab === tab.key && (
              <span
                className="absolute left-0 right-0 bottom-0 h-0.5 rounded-full"
                style={{ background: "var(--green-700)" }}
              />
            )}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {activeTab === "cv" && (
            <CvSkillsTab token={token} profileData={profileData} onUploaded={refresh} />
          )}
          {activeTab === "analysis" && <AnalysisTab token={token} profileData={profileData} />}
          {activeTab === "generator" && <GeneratorTab token={token} profileData={profileData} />}
        </div>

        <div className="space-y-6">
          <div className="card p-6">
            <div className="eyebrow mb-3">Plan &amp; settings</div>
            <div className="font-display text-xl mb-2">
              {TIER_LABELS[profileData.subscription_tier] || profileData.subscription_tier}
            </div>
            {subscriptionData && profileData.subscription_tier === "free" && (
              <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
                {subscriptionData.matches_used}/{subscriptionData.matches_limit} matches used
                {subscriptionData.welcome_bonus_active
                  ? ` (welcome bonus until ${formatWelcomeEnd(subscriptionData.welcome_match_bonus_until)})`
                  : " this month"}
              </p>
            )}
            <div className="flex flex-col gap-2">
              <Link href="/settings/billing" className="btn btn-outline w-full btn-sm justify-center gap-1.5">
                Billing &amp; plan
                <Icon name="arrowRight" size={14} />
              </Link>
              <Link
                href="/settings/job-preferences"
                className="btn btn-ghost w-full btn-sm justify-center gap-1.5"
              >
                Job preferences
                <Icon name="sliders" size={14} />
              </Link>
              <Link href="/settings/account" className="btn btn-ghost w-full btn-sm justify-center gap-1.5">
                Account settings
                <Icon name="settings" size={14} />
              </Link>
            </div>
          </div>

          <ProfileReferralCard
            userId={profileData.id}
            userName={profileData.full_name}
            referralCode={profileData.referral_code ?? ""}
            referralSignupsCount={profileData.referral_signups_count ?? 0}
            referralQualifiedCount={profileData.referral_qualified_count ?? 0}
          />

          <div className="card p-6">
            <div className="eyebrow mb-3">Quick links</div>
            <div className="flex flex-col gap-2 text-sm">
              <Link href="/settings/notifications" className="underline" style={{ color: "var(--green-700)" }}>
                Notification preferences
              </Link>
              <Link href="/settings/privacy" className="underline" style={{ color: "var(--green-700)" }}>
                Privacy &amp; data export
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
