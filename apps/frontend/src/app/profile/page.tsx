"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { profile as profileApi, type UserProfile } from "@/lib/api";
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

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter (K79/mo)",
  professional: "Professional (K199/mo)",
};

export default function ProfilePage() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [profileData, setProfileData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("cv");

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    profileApi
      .get(token)
      .then(setProfileData)
      .catch(() => setProfileData(null))
      .finally(() => setLoading(false));
  }, [token, isAuthenticated, authLoading, router]);

  const refresh = () => {
    if (!token) return;
    profileApi.get(token).then(setProfileData).catch(() => {});
  };

  if (loading || authLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-12">
        <div className="skeleton h-48 w-full mb-6" />
        <div className="skeleton h-64 w-full" />
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

  const fields = [
    !!profileData.full_name,
    !!profileData.phone,
    profileData.cv_uploaded,
    profileData.skills.length > 0,
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
            <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
              Upgrade to unlock tailored CVs and more matches.
            </p>
            <Link href="/pricing" className="btn btn-accent w-full btn-sm">
              Upgrade <Icon name="arrowRight" size={14} />
            </Link>
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
