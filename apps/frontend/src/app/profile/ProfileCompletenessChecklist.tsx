"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import type { ProfileCompletenessItem } from "@/lib/profileCompleteness";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
import type { JobPreferences, UserProfile } from "@/lib/api";
import { ProfileCompletenessModal } from "./ProfileCompletenessModal";

interface ProfileCompletenessChecklistProps {
  items: ProfileCompletenessItem[];
  token: string;
  profile: UserProfile;
  preferences: JobPreferences | null;
  onProfileSaved: (next: UserProfile) => void;
  onPreferencesSaved: (next: JobPreferences) => void;
}

export function ProfileCompletenessChecklist({
  items,
  token,
  profile,
  preferences,
  onProfileSaved,
  onPreferencesSaved,
}: ProfileCompletenessChecklistProps) {
  const [activeFieldId, setActiveFieldId] = useState<ProfileCompletenessFieldId | null>(null);

  const incomplete = items.filter((item) => !item.complete);
  if (incomplete.length === 0) return null;

  return (
    <>
      <div
        className="mt-4 rounded-lg p-4"
        style={{
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.12)",
        }}
      >
        <div className="text-xs font-medium mb-2" style={{ color: "var(--green-50)" }}>
          Complete your profile ({incomplete.length} remaining)
        </div>
        <ul className="space-y-2">
          {incomplete.map((item) => (
            <li key={item.id} className="flex items-start gap-2 text-xs">
              <span
                className="mt-0.5 shrink-0 inline-flex items-center justify-center rounded-full"
                style={{
                  width: 16,
                  height: 16,
                  border: "1px solid rgba(255,255,255,0.35)",
                }}
                aria-hidden
              />
              <span className="flex-1 min-w-0">
                <span style={{ color: "var(--green-50)" }}>{item.label}</span>
                <span style={{ color: "rgba(255,255,255,0.55)" }}> · +{item.weight}</span>
                <div style={{ color: "rgba(255,255,255,0.6)" }}>{item.hint}</div>
              </span>
              <button
                type="button"
                onClick={() => setActiveFieldId(item.id)}
                className="shrink-0 inline-flex items-center gap-0.5 underline"
                style={{
                  color: "var(--copper-300)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                }}
                aria-label={`Add ${item.label}`}
              >
                Add
                <Icon name="arrowRight" size={12} />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <ProfileCompletenessModal
        fieldId={activeFieldId}
        open={activeFieldId !== null}
        onClose={() => setActiveFieldId(null)}
        token={token}
        profile={profile}
        preferences={preferences}
        onProfileSaved={onProfileSaved}
        onPreferencesSaved={onPreferencesSaved}
      />
    </>
  );
}
