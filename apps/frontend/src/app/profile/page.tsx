"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { profile as profileApi, ApiError, type UserProfile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";

import { CvSkillsTab } from "./_tabs/CvSkillsTab";
import { AnalysisTab } from "./_tabs/AnalysisTab";
import { GeneratorTab } from "./_tabs/GeneratorTab";

type Tab = "cv" | "analysis" | "generator" | "preferences";

const TABS: { key: Tab; label: string }[] = [
  { key: "cv", label: "CV & Skills" },
  { key: "analysis", label: "CV Analysis" },
  { key: "generator", label: "CV Generator" },
  { key: "preferences", label: "Preferences" },
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
  "preferences": "preferences",
};

const SLUG_FROM_TAB: Record<Tab, string> = {
  cv: "cv-skills",
  analysis: "cv-analysis",
  generator: "cv-generator",
  preferences: "preferences",
};

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter (K125/mo)",
  professional: "Professional (K250/mo)",
  super_standard: "Super Standard (K500/mo)",
};

export default function ProfilePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const [profileData, setProfileData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize the tab from the `?tab=` URL slug so dropdown links like
  // /profile?tab=cv-generator actually open the right tab. Falls back to "cv"
  // for unknown / missing slugs.
  const tabSlug = searchParams.get("tab") ?? "cv";
  const initialTab: Tab = TAB_FROM_SLUG[tabSlug] ?? "cv";
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);

  // Keep state in sync when the URL changes (e.g. user navigates from nav
  // dropdown to a different tab via Link). Without this, the second click
  // is a no-op because the page is already mounted.
  useEffect(() => {
    const slug = searchParams.get("tab") ?? "cv";
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
    profileApi
      .get(token)
      .then(setProfileData)
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

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      <div className="card p-6 md:p-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          <div className="flex items-center gap-5 flex-1">
            <Avatar name={profileData.full_name || "User"} size={72} />
            <div>
              <h1 className="font-display text-3xl" style={{ letterSpacing: "-0.01em" }}>
                {profileData.full_name || "Your Profile"}
              </h1>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
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
            onClick={() => setActiveTab(tab.key)}
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
                style={{ background: "var(--copper-500)" }}
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
          {activeTab === "preferences" && (
            <div className="card p-6">
              <div className="eyebrow mb-4">Job preferences</div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Preference settings are coming soon. For now, your matches are based on your CV
                skills and location.
              </p>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card p-6">
            <div className="eyebrow mb-3">Your plan</div>
            <div className="font-display text-2xl mb-1">
              {TIER_LABELS[profileData.subscription_tier] || profileData.subscription_tier}
            </div>
            {/* Tier-aware sidebar — Professional and Super Standard users
                already have tailored CVs + generous match quotas. Showing
                "Upgrade to unlock tailored CVs" to them is misleading and
                erodes trust in the product. Top tiers see a "Manage plan"
                affordance instead; paid-but-not-top tiers see a tier-specific
                upsell; free sees the original upsell. Backend enforcement
                of paid features is unchanged — this is UI tier-gating only. */}
            {profileData.subscription_tier === "super_standard" ? (
              <>
                <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
                  You&apos;re on the top tier — unlimited matches, tailored CVs,
                  and priority support. Thanks for backing Zed CV.
                </p>
                <Link href="/pricing" className="btn btn-ghost w-full btn-sm">
                  Manage plan <Icon name="arrowRight" size={14} />
                </Link>
              </>
            ) : profileData.subscription_tier === "professional" ? (
              <>
                <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
                  Tailored CVs and 125 matches/month included. Move to Super
                  Standard for unlimited matches and daily WhatsApp digests.
                </p>
                <Link href="/pricing" className="btn btn-accent w-full btn-sm">
                  Upgrade <Icon name="arrowRight" size={14} />
                </Link>
              </>
            ) : (
              <>
                <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
                  Upgrade to unlock tailored CVs and more matches.
                </p>
                <Link href="/pricing" className="btn btn-accent w-full btn-sm">
                  Upgrade <Icon name="arrowRight" size={14} />
                </Link>
              </>
            )}
          </div>

          <div className="card p-6">
            <div className="eyebrow mb-3">Account</div>
            <div className="space-y-3">
              <div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>Name</div>
                <div className="text-sm font-medium">{profileData.full_name || "Not set"}</div>
              </div>
              <div>
                <div className="text-xs" style={{ color: "var(--muted)" }}>Phone</div>
                <div className="text-sm font-mono">{profileData.phone}</div>
              </div>
              {profileData.email && (
                <div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>Email</div>
                  <div className="text-sm">{profileData.email}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
