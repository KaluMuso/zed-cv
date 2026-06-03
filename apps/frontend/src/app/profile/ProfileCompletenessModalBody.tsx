"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  preferencesApi,
  profile as profileApi,
  type JobPreferences,
  type JobPreferencesUpdate,
  type UserProfile,
} from "@/lib/api";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
import { Icon } from "@/components/ui/Icon";
import { CvUploadField } from "@/components/profile/CvUploadField";
import {
  EducationLevelField,
  IndustriesField,
  LanguagesField,
  NoticePeriodField,
  RegionsField,
  RelocateField,
  SalaryExpectationsFields,
  validateSalaryRange,
  WorkArrangementField,
  YearsExperienceField,
} from "@/components/profile/preferences/PreferenceFields";
import { notify } from "@/lib/toast";
import {
  PREFERENCE_FIELD_CLASS,
  preferenceFieldStyle,
} from "@/components/profile/preferences/constants";

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
  const title = FIELD_TITLES[fieldId];
  const [saving, setSaving] = useState(false);

  const [fullName, setFullName] = useState(profile.full_name ?? "");
  const [email, setEmail] = useState(profile.email ?? "");
  const [yearsExperience, setYearsExperience] = useState(profile.years_experience ?? 0);

  const [prefs, setPrefs] = useState<JobPreferences | null>(preferences);
  const [loadingPrefs, setLoadingPrefs] = useState(!preferences);
  const [salaryError, setSalaryError] = useState<string | null>(null);

  useEffect(() => {
    setFullName(profile.full_name ?? "");
    setEmail(profile.email ?? "");
    setYearsExperience(profile.years_experience ?? 0);
  }, [profile, fieldId]);

  useEffect(() => {
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
  }, [preferences, token, fieldId]);

  const needsPreferences = PREFERENCE_FIELD_IDS.has(fieldId);
  const showSave =
    fieldId !== "phone" &&
    fieldId !== "cv_uploaded" &&
    fieldId !== "certifications";

  const savePreferences = async (patch: JobPreferencesUpdate) => {
    setSaving(true);
    try {
      const next = await preferencesApi.patch(token, patch);
      setPrefs(next);
      onPreferencesSaved(next);
      notify.success("Saved");
      onClose();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  };

  const saveProfile = async (patch: Parameters<typeof profileApi.update>[1]) => {
    setSaving(true);
    try {
      const next = await profileApi.update(token, patch);
      onProfileSaved(next);
      notify.success("Saved");
      onClose();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  };

  const onSaveClick = () => {
    if (!prefs && needsPreferences) return;

    switch (fieldId) {
      case "full_name":
        void saveProfile({ full_name: fullName.trim() || null });
        return;
      case "email":
        void saveProfile({ email: email.trim() || null });
        return;
      case "years_of_experience":
        void saveProfile({ years_experience: yearsExperience });
        return;
      case "preferred_work_arrangements":
        void savePreferences({
          preferred_work_arrangement: prefs?.preferred_work_arrangement ?? null,
        });
        return;
      case "preferred_locations":
        void savePreferences({ acceptable_regions: prefs?.acceptable_regions ?? [] });
        return;
      case "target_salary": {
        const err = validateSalaryRange(prefs?.salary_min ?? null, prefs?.salary_max ?? null);
        setSalaryError(err);
        if (err || !prefs) return;
        void savePreferences({
          salary_min: prefs.salary_min,
          salary_max: prefs.salary_max,
          salary_frequency: prefs.salary_frequency,
          salary_currency: prefs.salary_currency,
        });
        return;
      }
      case "education_level": {
        const extras = { ...(prefs?.extras ?? {}) };
        const level =
          typeof extras.education_level === "string" ? extras.education_level : "";
        if (level) extras.education_level = level;
        else delete extras.education_level;
        void savePreferences({ extras });
        return;
      }
      case "languages":
        void savePreferences({ languages: prefs?.languages ?? [] });
        return;
      case "preferred_industries":
        void savePreferences({ industries: prefs?.industries ?? [] });
        return;
      case "notice_period": {
        const extras = { ...(prefs?.extras ?? {}) };
        const period =
          typeof extras.notice_period === "string" ? extras.notice_period : "";
        if (period) extras.notice_period = period;
        else delete extras.notice_period;
        void savePreferences({ extras });
        return;
      }
      case "willing_to_relocate":
        void savePreferences({
          willing_to_relocate: prefs?.willing_to_relocate ?? false,
          preferred_work_arrangement: prefs?.preferred_work_arrangement ?? null,
        });
        return;
      default:
        return;
    }
  };

  let body: React.ReactNode;

  if (fieldId === "phone") {
    body = (
      <p className="text-sm" style={{ color: "var(--muted)" }}>
        Your phone number is verified at sign-up ({profile.phone || "not set"}). To change it,
        contact support or sign in with a different number.
      </p>
    );
  } else if (fieldId === "cv_uploaded") {
    body = (
      <CvUploadField
        token={token}
        cvUploaded={profile.cv_uploaded}
        onUploaded={() => {
          notify.success("CV uploaded");
          onProfileSaved({ ...profile, cv_uploaded: true });
          onClose();
        }}
      />
    );
  } else if (fieldId === "certifications") {
    body = (
      <div className="space-y-3 text-sm" style={{ color: "var(--muted)" }}>
        <p>
          Certifications are read from your uploaded CV. Upload or replace your CV to add them, or
          list them in the CV &amp; Skills tab.
        </p>
        <CvUploadField
          token={token}
          cvUploaded={profile.cv_uploaded}
          onUploaded={() => {
            notify.success("CV updated");
            onProfileSaved({ ...profile, cv_uploaded: true });
          }}
        />
      </div>
    );
  } else if (loadingPrefs || !prefs) {
    body = <p className="text-sm" style={{ color: "var(--muted)" }}>Loading…</p>;
  } else {
    const educationLevel =
      typeof prefs.extras?.education_level === "string" ? prefs.extras.education_level : "";
    const noticePeriod =
      typeof prefs.extras?.notice_period === "string" ? prefs.extras.notice_period : "";

    body = (
      <div className="space-y-4">
        {fieldId === "full_name" && (
          <AccountTextField label="Full name" value={fullName} onChange={setFullName} />
        )}
        {fieldId === "email" && (
          <AccountTextField
            label="Email address"
            value={email}
            onChange={setEmail}
            type="email"
          />
        )}
        {fieldId === "years_of_experience" && (
          <YearsExperienceField value={yearsExperience} onChange={setYearsExperience} />
        )}
        {fieldId === "preferred_work_arrangements" && (
          <WorkArrangementField
            value={prefs.preferred_work_arrangement}
            onChange={(v) => setPrefs({ ...prefs, preferred_work_arrangement: v })}
          />
        )}
        {fieldId === "willing_to_relocate" && (
          <div className="space-y-4">
            <RelocateField
              checked={prefs.willing_to_relocate}
              onChange={(checked) => setPrefs({ ...prefs, willing_to_relocate: checked })}
            />
            <WorkArrangementField
              value={prefs.preferred_work_arrangement}
              onChange={(v) => setPrefs({ ...prefs, preferred_work_arrangement: v })}
            />
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Saving any work preference marks relocation as answered for your profile score.
            </p>
          </div>
        )}
        {fieldId === "preferred_locations" && (
          <RegionsField
            value={prefs.acceptable_regions}
            onChange={(regions) => setPrefs({ ...prefs, acceptable_regions: regions })}
          />
        )}
        {fieldId === "target_salary" && (
          <SalaryExpectationsFields
            preferences={prefs}
            salaryError={salaryError}
            onChange={(patch) => {
              setPrefs({ ...prefs, ...patch });
              const nextMin = patch.salary_min !== undefined ? patch.salary_min : prefs.salary_min;
              const nextMax = patch.salary_max !== undefined ? patch.salary_max : prefs.salary_max;
              setSalaryError(validateSalaryRange(nextMin, nextMax));
            }}
          />
        )}
        {fieldId === "education_level" && (
          <EducationLevelField
            value={educationLevel}
            onChange={(level) => {
              const extras = { ...(prefs.extras || {}) };
              if (level) extras.education_level = level;
              else delete extras.education_level;
              setPrefs({ ...prefs, extras });
            }}
          />
        )}
        {fieldId === "languages" && (
          <LanguagesField
            value={prefs.languages}
            onChange={(languages) => setPrefs({ ...prefs, languages })}
          />
        )}
        {fieldId === "preferred_industries" && (
          <IndustriesField
            value={prefs.industries}
            onChange={(industries) => setPrefs({ ...prefs, industries })}
          />
        )}
        {fieldId === "notice_period" && (
          <NoticePeriodField
            value={noticePeriod}
            onChange={(period) => {
              const extras = { ...(prefs.extras || {}) };
              if (period) extras.notice_period = period;
              else delete extras.notice_period;
              setPrefs({ ...prefs, extras });
            }}
          />
        )}
      </div>
    );
  }

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
      <div className="p-5 sm:p-6 overflow-y-auto flex-1">{body}</div>
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
            onClick={onSaveClick}
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

function AccountTextField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="text-xs block" style={{ color: "var(--muted)" }}>
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      />
    </label>
  );
}

const FIELD_TITLES: Record<ProfileCompletenessFieldId, string> = {
  phone: "Phone number",
  email: "Email address",
  full_name: "Full name",
  cv_uploaded: "CV uploaded",
  years_of_experience: "Years of experience",
  preferred_industries: "Preferred industries",
  preferred_work_arrangements: "Work arrangement",
  preferred_locations: "Preferred locations",
  target_salary: "Salary expectations",
  education_level: "Education level",
  languages: "Languages",
  certifications: "Certifications",
  notice_period: "Notice period",
  willing_to_relocate: "Relocation preference",
};

const PREFERENCE_FIELD_IDS = new Set<ProfileCompletenessFieldId>([
  "years_of_experience",
  "preferred_industries",
  "preferred_work_arrangements",
  "preferred_locations",
  "target_salary",
  "education_level",
  "languages",
  "notice_period",
  "willing_to_relocate",
]);
