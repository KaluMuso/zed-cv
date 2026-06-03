"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  preferencesApi,
  profile as profileApi,
  type JobPreferences,
  type UserProfile,
} from "@/lib/api";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
import { buildCompletenessSavePatch } from "./buildCompletenessSavePatch";
import {
  fieldNeedsPreferencesLoad,
  fieldShowsSaveButton,
  PROFILE_COMPLETENESS_FIELD_TITLES,
} from "./profileCompletenessModalConfig";
import { ProfileCompletenessModalContent } from "./ProfileCompletenessModalContent";

export function ProfileCompletenessModalBody({
  fieldId,
  token,
  profile,
  preferences,
  onClose,
  onProfileSaved,
  onPreferencesSaved,
}: {
  fieldId: ProfileCompletenessFieldId;
  token: string;
  profile: UserProfile;
  preferences: JobPreferences | null;
  onClose: () => void;
  onProfileSaved: (next: UserProfile) => void;
  onPreferencesSaved: (next: JobPreferences) => void;
}) {
  const title = PROFILE_COMPLETENESS_FIELD_TITLES[fieldId];
  const [saving, setSaving] = useState(false);
  const [fullName, setFullName] = useState(profile.full_name ?? "");
  const [email, setEmail] = useState(profile.email ?? "");
  const [yearsExperience, setYearsExperience] = useState(profile.years_experience ?? 0);
  const [prefs, setPrefs] = useState<JobPreferences | null>(preferences);
  const [loadingPrefs, setLoadingPrefs] = useState(fieldNeedsPreferencesLoad(fieldId) && !preferences);
  const [salaryError, setSalaryError] = useState<string | null>(null);

  const needsPreferences = fieldNeedsPreferencesLoad(fieldId);
  const showSave = fieldShowsSaveButton(fieldId);

  useEffect(() => {
    setFullName(profile.full_name ?? "");
    setEmail(profile.email ?? "");
    setYearsExperience(profile.years_experience ?? 0);
  }, [profile, fieldId]);

  useEffect(() => {
    if (!needsPreferences) {
      setLoadingPrefs(false);
      return;
    }
    if (preferences) {
      setPrefs(preferences);
      setLoadingPrefs(false);
      return;
    }
    let cancelled = false;
    setLoadingPrefs(true);
    preferencesApi
      .get(token)
      .then((data) => {
        if (!cancelled) setPrefs(data);
      })
      .catch(() => {
        if (!cancelled) notify.error("Could not load preferences");
      })
      .finally(() => {
        if (!cancelled) setLoadingPrefs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [preferences, token, fieldId, needsPreferences]);

  const onSaveClick = async () => {
    const target = buildCompletenessSavePatch(fieldId, prefs, {
      fullName,
      email,
      yearsExperience,
    });
    if (!target) return;
    if (target.kind === "invalid") {
      setSalaryError(target.salaryError);
      return;
    }

    setSaving(true);
    try {
      if (target.kind === "profile") {
        const next = await profileApi.update(token, target.patch);
        onProfileSaved(next);
      } else {
        const next = await preferencesApi.patch(token, target.patch);
        setPrefs(next);
        onPreferencesSaved(next);
      }
      notify.success("Saved");
      onClose();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <header
        className="flex items-start justify-between gap-4 p-5 sm:p-6 border-b shrink-0"
        style={{ borderColor: "var(--line)" }}
      >
        <div>
          <div className="eyebrow mb-1">Complete profile</div>
          <h2
            id="profile-completeness-modal-title"
            className="font-display text-xl sm:text-2xl"
            style={{ letterSpacing: "-0.01em" }}
          >
            {title}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style={{ border: "1px solid var(--line-2)", color: "var(--muted)" }}
        >
          <Icon name="x" size={16} />
        </button>
      </header>
      <div className="p-5 sm:p-6 overflow-y-auto flex-1">
        <ProfileCompletenessModalContent
          fieldId={fieldId}
          token={token}
          profile={profile}
          loadingPrefs={needsPreferences && loadingPrefs}
          prefs={prefs}
          form={{ fullName, email, yearsExperience, salaryError }}
          handlers={{
            setFullName,
            setEmail,
            setYearsExperience,
            setPrefs: (value) => {
              setPrefs((prev) => {
                const base = prev ?? mockEmptyPrefs();
                return typeof value === "function" ? value(base) : value;
              });
            },
            setSalaryError,
          }}
          onProfileSaved={onProfileSaved}
          onClose={onClose}
        />
      </div>
      <footer
        className="flex flex-wrap items-center justify-end gap-2 p-5 sm:p-6 border-t shrink-0"
        style={{ borderColor: "var(--line)" }}
      >
        {fieldId === "email" || fieldId === "full_name" ? (
          <Link
            href="/settings/account"
            className="text-xs underline mr-auto"
            style={{ color: "var(--green-700)" }}
          >
            Account settings
          </Link>
        ) : null}
        <button type="button" onClick={onClose} className="btn btn-ghost btn-sm">
          {showSave ? "Cancel" : "Close"}
        </button>
        {showSave ? (
          <button
            type="button"
            onClick={() => void onSaveClick()}
            disabled={saving || (needsPreferences && (loadingPrefs || !prefs))}
            className="btn btn-primary btn-sm"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        ) : null}
      </footer>
    </>
  );
}

function mockEmptyPrefs(): JobPreferences {
  return {
    target_roles: [],
    target_roles_source: "user_provided",
    salary_min: null,
    salary_max: null,
    salary_currency: "ZMW",
    salary_frequency: null,
    preferred_work_arrangement: null,
    willing_to_relocate: false,
    acceptable_regions: [],
    languages: [],
    industries: [],
    extras: {},
    auto_populated_at: null,
    manually_updated_at: null,
    auto_populated_fields: [],
  };
}
