"use client";

import type { JobPreferences, UserProfile } from "@/lib/api";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
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
import {
  PREFERENCE_FIELD_CLASS,
  preferenceFieldStyle,
} from "@/components/profile/preferences/constants";
import { notify } from "@/lib/toast";

export interface PreferenceFormState {
  fullName: string;
  email: string;
  yearsExperience: number;
  salaryError: string | null;
}

export interface PreferenceFormHandlers {
  setFullName: (v: string) => void;
  setEmail: (v: string) => void;
  setYearsExperience: (v: number) => void;
  setPrefs: React.Dispatch<React.SetStateAction<JobPreferences>>;
  setSalaryError: (v: string | null) => void;
}

export function ProfileCompletenessModalContent({
  fieldId,
  token,
  profile,
  loadingPrefs,
  prefs,
  form,
  handlers,
  onProfileSaved,
  onClose,
}: {
  fieldId: ProfileCompletenessFieldId;
  token: string;
  profile: UserProfile;
  loadingPrefs: boolean;
  prefs: JobPreferences | null;
  form: PreferenceFormState;
  handlers: PreferenceFormHandlers;
  onProfileSaved: (next: UserProfile) => void;
  onClose: () => void;
}) {
  if (fieldId === "phone") {
    return (
      <p className="text-sm" style={{ color: "var(--muted)" }}>
        Your phone number is verified at sign-up ({profile.phone || "not set"}). To change it,
        contact support or sign in with a different number.
      </p>
    );
  }

  if (fieldId === "cv_uploaded") {
    return (
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
  }

  if (fieldId === "certifications") {
    return (
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
  }

  if (loadingPrefs || !prefs) {
    return <p className="text-sm" style={{ color: "var(--muted)" }}>Loading…</p>;
  }

  const educationLevel =
    typeof prefs.extras?.education_level === "string" ? prefs.extras.education_level : "";
  const noticePeriod =
    typeof prefs.extras?.notice_period === "string" ? prefs.extras.notice_period : "";

  return (
    <div className="space-y-4">
      {fieldId === "full_name" && (
        <AccountTextField
          label="Full name"
          value={form.fullName}
          onChange={handlers.setFullName}
        />
      )}
      {fieldId === "email" && (
        <AccountTextField
          label="Email address"
          value={form.email}
          onChange={handlers.setEmail}
          type="email"
        />
      )}
      {fieldId === "years_of_experience" && (
        <YearsExperienceField
          value={form.yearsExperience}
          onChange={handlers.setYearsExperience}
        />
      )}
      {fieldId === "preferred_work_arrangements" && (
        <WorkArrangementField
          value={prefs.preferred_work_arrangement}
          onChange={(v) => handlers.setPrefs({ ...prefs, preferred_work_arrangement: v })}
        />
      )}
      {fieldId === "willing_to_relocate" && (
        <div className="space-y-4">
          <RelocateField
            checked={prefs.willing_to_relocate}
            onChange={(checked) => handlers.setPrefs({ ...prefs, willing_to_relocate: checked })}
          />
          <WorkArrangementField
            value={prefs.preferred_work_arrangement}
            onChange={(v) => handlers.setPrefs({ ...prefs, preferred_work_arrangement: v })}
          />
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Saving any work preference marks relocation as answered for your profile score.
          </p>
        </div>
      )}
      {fieldId === "preferred_locations" && (
        <RegionsField
          value={prefs.acceptable_regions}
          onChange={(regions) => handlers.setPrefs({ ...prefs, acceptable_regions: regions })}
        />
      )}
      {fieldId === "target_salary" && (
        <SalaryExpectationsFields
          preferences={prefs}
          salaryError={form.salaryError}
          onChange={(patch) => {
            handlers.setPrefs({ ...prefs, ...patch });
            const nextMin = patch.salary_min !== undefined ? patch.salary_min : prefs.salary_min;
            const nextMax = patch.salary_max !== undefined ? patch.salary_max : prefs.salary_max;
            handlers.setSalaryError(validateSalaryRange(nextMin, nextMax));
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
            handlers.setPrefs({ ...prefs, extras });
          }}
        />
      )}
      {fieldId === "languages" && (
        <LanguagesField
          value={prefs.languages}
          onChange={(languages) => handlers.setPrefs({ ...prefs, languages })}
        />
      )}
      {fieldId === "preferred_industries" && (
        <IndustriesField
          value={prefs.industries}
          onChange={(industries) => handlers.setPrefs({ ...prefs, industries })}
        />
      )}
      {fieldId === "notice_period" && (
        <NoticePeriodField
          value={noticePeriod}
          onChange={(period) => {
            const extras = { ...(prefs.extras || {}) };
            if (period) extras.notice_period = period;
            else delete extras.notice_period;
            handlers.setPrefs({ ...prefs, extras });
          }}
        />
      )}
    </div>
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
  const inputId = `profile-completeness-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <label htmlFor={inputId} className="text-xs block" style={{ color: "var(--muted)" }}>
      {label}
      <input
        id={inputId}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      />
    </label>
  );
}
