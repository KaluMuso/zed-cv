"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  profile as profileApi,
  cv as cvApi,
  type UserProfile,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import Link from "next/link";

type Tab = "cv" | "preferences";

export default function ProfilePage() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [profileData, setProfileData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("cv");
  const fileRef = useRef<HTMLInputElement>(null);

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

  const handleUpload = useCallback(
    async (file: File) => {
      if (!token) return;
      const validTypes = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
      ];
      if (!validTypes.includes(file.type)) {
        setUploadMsg("Please upload a PDF, Word document, or image.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadMsg("File must be under 10MB.");
        return;
      }
      setUploading(true);
      setUploadMsg("");
      try {
        const result = await cvApi.upload(token, file);
        setUploadMsg(
          `CV uploaded! ${result.skills_extracted.length} skills extracted.`
        );
        const updated = await profileApi.get(token);
        setProfileData(updated);
      } catch (err) {
        setUploadMsg(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [token]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  if (loading || authLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-12">
        <div className="skeleton h-48 w-full mb-6" />
        <div className="skeleton h-64 w-full" />
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-20 text-center">
        <p style={{ color: "var(--muted)" }}>Could not load profile.</p>
      </div>
    );
  }

  const tierLabels: Record<string, string> = {
    free: "Free",
    starter: "Starter (K125/mo)",
    professional: "Professional (K250/mo)",
  };

  // Completeness
  const fields = [
    !!profileData.full_name,
    !!profileData.phone,
    profileData.cv_uploaded,
    profileData.skills.length > 0,
  ];
  const completeness = Math.round(
    (fields.filter(Boolean).length / fields.length) * 100
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "cv", label: "CV & Skills" },
    { key: "preferences", label: "Preferences" },
  ];

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      {/* Header card */}
      <div className="card p-6 md:p-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          <div className="flex items-center gap-5 flex-1">
            <Avatar
              name={profileData.full_name || "User"}
              size={72}
            />
            <div>
              <h1
                className="font-display text-3xl"
                style={{ letterSpacing: "-0.01em" }}
              >
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
                  {tierLabels[profileData.subscription_tier] ||
                    profileData.subscription_tier}
                </span>
              </div>
            </div>
          </div>

          {/* Completeness ring */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <svg width={80} height={80} className="-rotate-90">
                <circle
                  cx={40}
                  cy={40}
                  r={34}
                  fill="none"
                  className="score-ring-track"
                  strokeWidth={5}
                />
                <circle
                  cx={40}
                  cy={40}
                  r={34}
                  fill="none"
                  stroke="var(--copper-500)"
                  strokeWidth={5}
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 34}
                  strokeDashoffset={
                    2 * Math.PI * 34 -
                    (completeness / 100) * 2 * Math.PI * 34
                  }
                  style={{
                    transition:
                      "stroke-dashoffset 1s cubic-bezier(0.2,0.7,0.2,1)",
                  }}
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
                {completeness < 100
                  ? "Add more details to improve matches"
                  : "Looking great!"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex gap-6 mb-8"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className="pb-3 text-sm font-medium relative"
            style={{
              color:
                activeTab === tab.key ? "var(--ink)" : "var(--muted)",
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
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {activeTab === "cv" && (
            <>
              {/* CV Upload */}
              <div className="card p-6">
                <div className="eyebrow mb-4">
                  {profileData.cv_uploaded ? "Your CV" : "Upload your CV"}
                </div>

                {profileData.cv_uploaded && (
                  <div
                    className="flex items-center gap-3 p-3 rounded-lg mb-4"
                    style={{
                      background: "var(--bg-2)",
                      border: "1px solid var(--line)",
                    }}
                  >
                    <Icon name="file" size={20} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        CV uploaded
                      </div>
                      <div className="text-xs" style={{ color: "var(--muted)" }}>
                        {profileData.skills.length} skills extracted
                      </div>
                    </div>
                    <button
                      onClick={() => fileRef.current?.click()}
                      className="btn btn-ghost btn-sm"
                    >
                      Replace
                    </button>
                  </div>
                )}

                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragActive(true);
                  }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={onDrop}
                  onClick={() => fileRef.current?.click()}
                  className="cursor-pointer p-8 text-center rounded-xl transition"
                  style={{
                    border: dragActive
                      ? "2px dashed var(--green-500)"
                      : "2px dashed var(--line-2)",
                    background: dragActive ? "var(--green-50)" : "transparent",
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") fileRef.current?.click();
                  }}
                >
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    onChange={onFileChange}
                    className="hidden"
                  />
                  {uploading ? (
                    <div className="flex items-center justify-center gap-2">
                      <span className="spinner" style={{ borderTopColor: "var(--green-500)", borderColor: "var(--line-2)" }} />
                      <span className="text-sm font-medium" style={{ color: "var(--green-700)" }}>
                        Uploading...
                      </span>
                    </div>
                  ) : (
                    <>
                      <div
                        className="w-12 h-12 mx-auto mb-3 rounded-xl flex items-center justify-center"
                        style={{
                          background: "var(--bg-2)",
                          color: "var(--muted)",
                        }}
                      >
                        <Icon name="upload" size={22} />
                      </div>
                      <p className="text-sm" style={{ color: "var(--ink-2)" }}>
                        Drag and drop your CV here, or{" "}
                        <span
                          className="font-medium"
                          style={{ color: "var(--green-700)" }}
                        >
                          browse
                        </span>
                      </p>
                      <p
                        className="text-xs mt-1"
                        style={{ color: "var(--muted)" }}
                      >
                        PDF, Word, or image (max 10MB)
                      </p>
                    </>
                  )}
                </div>

                {uploadMsg && (
                  <p
                    className="mt-3 text-sm"
                    style={{
                      color:
                        uploadMsg.includes("failed") ||
                        uploadMsg.includes("Please")
                          ? "var(--danger)"
                          : "var(--success)",
                    }}
                  >
                    {uploadMsg}
                  </p>
                )}
              </div>

              {/* Extracted Skills */}
              <div className="card p-6">
                <div className="eyebrow mb-4">Extracted skills</div>
                {profileData.skills.length === 0 ? (
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    Upload your CV to automatically extract skills.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {profileData.skills.map((skill) => (
                      <SkillBadge key={skill} skill={skill} matched />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === "preferences" && (
            <div className="card p-6">
              <div className="eyebrow mb-4">Job preferences</div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Preference settings are coming soon. For now, your matches are
                based on your CV skills and location.
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Plan card */}
          <div className="card p-6">
            <div className="eyebrow mb-3">Your plan</div>
            <div className="font-display text-2xl mb-1">
              {tierLabels[profileData.subscription_tier] ||
                profileData.subscription_tier}
            </div>
            <p
              className="text-sm mb-4"
              style={{ color: "var(--muted)" }}
            >
              Upgrade to unlock tailored CVs and more matches.
            </p>
            <Link href="/pricing" className="btn btn-accent w-full btn-sm">
              Upgrade <Icon name="arrowRight" size={14} />
            </Link>
          </div>

          {/* Quick info */}
          <div className="card p-6">
            <div className="eyebrow mb-3">Account</div>
            <div className="space-y-3">
              <div>
                <div
                  className="text-xs"
                  style={{ color: "var(--muted)" }}
                >
                  Name
                </div>
                <div className="text-sm font-medium">
                  {profileData.full_name || "Not set"}
                </div>
              </div>
              <div>
                <div
                  className="text-xs"
                  style={{ color: "var(--muted)" }}
                >
                  Phone
                </div>
                <div className="text-sm font-mono">
                  {profileData.phone}
                </div>
              </div>
              {profileData.email && (
                <div>
                  <div
                    className="text-xs"
                    style={{ color: "var(--muted)" }}
                  >
                    Email
                  </div>
                  <div className="text-sm">
                    {profileData.email}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
