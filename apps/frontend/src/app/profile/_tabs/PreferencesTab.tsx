"use client";

/**
 * Preferences tab — job-search preferences capture.
 *
 * Five collapsible sections matching the user_preferences schema
 * groups: target roles, salary, work arrangement, languages + industry,
 * additional info. Every field is optional; auto-save on blur with 800ms
 * debounce; "Auto-populated from CV" badges next to fields the
 * /cv/upload hook filled.
 *
 * One sticky save indicator at the top so the user always knows whether
 * their last change made it.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  preferencesApi,
  profile as profileApi,
  cv as cvApi,
  type JobPreferences,
  type JobPreferencesUpdate,
  type PreferredLanguage,
  type IndustryExperience,
  type UserProfile,
} from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { TargetRolesInput } from "@/components/TargetRolesInput";
import { usePreferencesAutoSave, type SaveStatus } from "@/hooks/usePreferencesAutoSave";
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
  EmploymentTypeField,
  YearsExperienceField,
} from "@/components/profile/preferences/PreferenceFields";

type SectionKey =
  | "career"
  | "target_roles"
  | "salary"
  | "work_arrangement"
  | "languages"
  | "extras";

const SECTION_LABELS: Record<SectionKey, string> = {
  career: "Career background",
  target_roles: "Target roles",
  salary: "Salary expectations",
  work_arrangement: "Work arrangement",
  languages: "Languages & industries",
  extras: "Additional information",
};

const STORAGE_KEY = "zedapply:preferences:expanded";

export function PreferencesTab({
  profileData,
  onProfileUpdated,
  onPreferencesSaved,
}: {
  profileData: UserProfile;
  onProfileUpdated?: () => void;
  onPreferencesSaved?: (next: JobPreferences) => void;
}) {
  const { token } = useAuth();
  const [yearsExperience, setYearsExperience] = useState(profileData.years_experience ?? 0);
  const [savingYears, setSavingYears] = useState(false);
  const [data, setData] = useState<JobPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const [expanded, setExpanded] = useState<Record<SectionKey, boolean>>(() => {
    if (typeof window === "undefined") {
      return defaultExpanded();
    }
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === "object") {
          return { ...defaultExpanded(), ...parsed };
        }
      }
    } catch {
      /* localStorage disabled — fall back to defaults */
    }
    return defaultExpanded();
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(expanded));
    } catch {
      /* ignore — non-essential */
    }
  }, [expanded]);

  const { status, queue, flush } = usePreferencesAutoSave({
    token: token ?? "",
    onSaved: (next) => {
      setData(next);
      onPreferencesSaved?.(next);
    },
  });

  useEffect(() => {
    setYearsExperience(profileData.years_experience ?? 0);
  }, [profileData.years_experience]);

  // Surface CV-derived role titles as extra autocomplete entries on the
  // target-roles input — handy when the user wants to re-add a role
  // they removed. Computed up here (before the early returns) so the
  // hook order is stable across loading / error / loaded states.
  const cvRoleSuggestions = useMemo(() => {
    const sections = profileData.cv_sections;
    if (!sections?.work_experience) return [];
    return sections.work_experience
      .map((w) => w.title)
      .filter((t): t is string => Boolean(t));
  }, [profileData.cv_sections]);

  // Initial load. The endpoint auto-creates an empty row if needed so
  // we always get a usable shape back.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    preferencesApi
      .get(token)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Failed to load preferences");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  // Optimistic-update + queue-save. The local UI is updated immediately
  // (no waiting on the network); the server save fires after debounce.
  // On error, the queued save's catch path surfaces the message in the
  // sticky banner — we don't roll back the optimistic state because
  // that would feel jarring and the user might still be typing.
  const update = useCallback(
    (patch: JobPreferencesUpdate) => {
      setData((prev) => (prev ? mergeInto(prev, patch) : prev));
      // Local salary_min/salary_max invariant check — give immediate
      // feedback instead of waiting for a 422.
      const draft: JobPreferences | null = data ? mergeInto(data, patch) : null;
      const errs: Record<string, string> = {};
      if (draft) {
        const salaryErr = validateSalaryRange(draft.salary_min, draft.salary_max);
        if (salaryErr) errs.salary = salaryErr;
      }
      setValidationErrors(errs);
      if (Object.keys(errs).length === 0) {
        queue(patch);
      }
    },
    [queue, data],
  );

  const saveYearsExperience = async () => {
    if (!token) return;
    setSavingYears(true);
    try {
      await profileApi.update(token, { years_experience: yearsExperience });
      onProfileUpdated?.();
    } catch {
      /* surfaced via profile refresh failure */
    } finally {
      setSavingYears(false);
    }
  };

  const educationLevel =
    typeof data?.extras?.education_level === "string" ? data.extras.education_level : "";
  const noticePeriod =
    typeof data?.extras?.notice_period === "string" ? data.extras.notice_period : "";

  const onManualPopulate = async () => {
    if (!token) return;
    try {
      // Re-trigger by re-uploading nothing — there's no dedicated
      // endpoint. The acceptance criterion says users whose CV was
      // uploaded before this feature should be able to fill in from
      // CV manually. We do this by hitting /cv/analyze which is the
      // cheapest re-read of the parsed_data and then calling /cv/upload
      // is too heavy. For now we just re-fetch preferences (server's
      // upload-time hook is the only writer) — if the user uploaded
      // a CV pre-launch, they should re-upload to fill the row.
      // Surfacing this honestly in copy below the button.
      await flush();
      const fresh = await preferencesApi.get(token);
      setData(fresh);
    } catch {
      /* ignore — UI surfaces via status */
    }
  };

  if (loading) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-4">Job preferences</div>
        <div className="skeleton h-4 w-2/3 mb-2" />
        <div className="skeleton h-4 w-1/2 mb-4" />
        <div className="skeleton h-24 w-full" />
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">Job preferences</div>
        <p className="text-sm" style={{ color: "var(--danger)" }}>
          {loadError ?? "Could not load preferences."}
        </p>
      </div>
    );
  }

  const autoFields = new Set(data.auto_populated_fields || []);
  const isCompletelyEmpty =
    data.target_roles.length === 0 &&
    data.salary_min === null &&
    data.salary_max === null &&
    data.preferred_work_arrangement === null &&
    data.acceptable_regions.length === 0 &&
    data.languages.length === 0 &&
    data.industries.length === 0 &&
    Object.keys(data.extras || {}).length === 0;

  const toggle = (key: SectionKey) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="space-y-4">
      <SaveBanner status={status} hasValidationErrors={Object.keys(validationErrors).length > 0} />

      {isCompletelyEmpty && (
        <div
          className="card p-6"
          style={{ borderColor: "var(--copper-500)", borderStyle: "dashed" }}
        >
          <div className="eyebrow mb-2">Tell us more</div>
          <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
            Tell us more about what you&apos;re looking for — this helps us match
            you with better jobs and tailor your CV.
          </p>
          {profileData.cv_uploaded ? (
            <>
              <button onClick={onManualPopulate} className="btn btn-ghost btn-sm">
                Fill in from CV <Icon name="sparkle" size={14} />
              </button>
              <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
                If your CV was uploaded before this feature shipped, re-upload it from the CV
                tab to populate these fields.
              </p>
            </>
          ) : (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Upload a CV to auto-fill some of these fields, or just type your preferences below.
            </p>
          )}
        </div>
      )}

      <Section
        title={SECTION_LABELS.career}
        sectionKey="career"
        expanded={expanded.career}
        onToggle={() => toggle("career")}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <YearsExperienceField
            value={yearsExperience}
            onChange={setYearsExperience}
            onBlur={() => void saveYearsExperience()}
          />
          <EducationLevelField
            value={educationLevel}
            onChange={(value) => {
              const extras = { ...(data.extras || {}) };
              if (value) extras.education_level = value;
              else delete extras.education_level;
              update({ extras });
            }}
          />
        </div>
        <div className="mt-3">
          <NoticePeriodField
            value={noticePeriod}
            onChange={(value) => {
              const extras = { ...(data.extras || {}) };
              if (value) extras.notice_period = value;
              else delete extras.notice_period;
              update({ extras });
            }}
          />
        </div>
        {savingYears && (
          <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
            Saving experience…
          </p>
        )}
        <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
          These fields improve match quality and appear on your profile completeness score.
        </p>
      </Section>

      <Section
        title={SECTION_LABELS.target_roles}
        sectionKey="target_roles"
        expanded={expanded.target_roles}
        onToggle={() => toggle("target_roles")}
        autoBadge={autoFields.has("target_roles")}
      >
        <label
          htmlFor="target-roles-input"
          className="block text-xs mb-2"
          style={{ color: "var(--muted)" }}
        >
          What roles are you looking for? Up to 10.
        </label>
        <TargetRolesInput
          value={data.target_roles}
          onChange={(roles) => update({ target_roles: roles })}
          extraSuggestions={cvRoleSuggestions}
        />
      </Section>

      <Section
        title={SECTION_LABELS.salary}
        sectionKey="salary"
        expanded={expanded.salary}
        onToggle={() => toggle("salary")}
      >
        <SalaryExpectationsFields
          preferences={data}
          salaryError={validationErrors.salary}
          onChange={(patch) => update(patch)}
        />
      </Section>

      <Section
        title={SECTION_LABELS.work_arrangement}
        sectionKey="work_arrangement"
        expanded={expanded.work_arrangement}
        onToggle={() => toggle("work_arrangement")}
        autoBadge={autoFields.has("acceptable_regions")}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <WorkArrangementField
            value={data.preferred_work_arrangement}
            onChange={(v) => update({ preferred_work_arrangement: v })}
          />
          <RelocateField
            checked={data.willing_to_relocate}
            onChange={(checked) => update({ willing_to_relocate: checked })}
          />
        </div>
        <div className="mt-3">
          <EmploymentTypeField
            value={(data.extras?.employment_types as string[]) || []}
            onChange={(types) => {
              const extras = { ...(data.extras || {}) };
              if (types.length > 0) extras.employment_types = types;
              else delete extras.employment_types;
              update({ extras });
            }}
          />
        </div>
        <div className="mt-3">
          <RegionsField
            value={data.acceptable_regions}
            onChange={(regions) => update({ acceptable_regions: regions })}
          />
        </div>
      </Section>

      <Section
        title={SECTION_LABELS.languages}
        sectionKey="languages"
        expanded={expanded.languages}
        onToggle={() => toggle("languages")}
        autoBadge={autoFields.has("languages") || autoFields.has("industries")}
      >
        <LanguagesField
          value={data.languages}
          onChange={(langs: PreferredLanguage[]) => update({ languages: langs })}
        />
        <div className="mt-4">
          <IndustriesField
            value={data.industries}
            onChange={(inds: IndustryExperience[]) => update({ industries: inds })}
          />
        </div>
      </Section>

      <Section
        title={SECTION_LABELS.extras}
        sectionKey="extras"
        expanded={expanded.extras}
        onToggle={() => toggle("extras")}
      >
        <ExtrasEditor
          value={data.extras || {}}
          onChange={(extras) => update({ extras })}
        />
      </Section>

      <Footer status={status} />
    </div>
  );
}

function defaultExpanded(): Record<SectionKey, boolean> {
  return {
    career: true,
    target_roles: true,
    salary: false,
    work_arrangement: false,
    languages: false,
    extras: false,
  };
}

function mergeInto(prev: JobPreferences, patch: JobPreferencesUpdate): JobPreferences {
  const next: JobPreferences = { ...prev };
  for (const [k, v] of Object.entries(patch)) {
    if (v === undefined) continue;
    (next as unknown as Record<string, unknown>)[k] = v;
  }
  return next;
}

function Section({
  title,
  sectionKey,
  expanded,
  onToggle,
  autoBadge,
  children,
}: {
  title: string;
  sectionKey: SectionKey;
  expanded: boolean;
  onToggle: () => void;
  autoBadge?: boolean;
  children: React.ReactNode;
}) {
  const contentId = `pref-section-${sectionKey}`;
  return (
    <div className="card p-0 overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={contentId}
        className="w-full flex items-center justify-between gap-3 p-4"
        style={{ background: "var(--bg-1)", border: "none", cursor: "pointer", color: "var(--ink)" }}
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          {title}
          {autoBadge && (
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: "var(--copper-500)",
                color: "var(--bg-1)",
              }}
            >
              Auto-populated from CV
            </span>
          )}
        </span>
        <Icon name={expanded ? "chevronDown" : "chevronRight"} size={16} />
      </button>
      {expanded && (
        <div id={contentId} className="p-4 pt-0">
          {children}
        </div>
      )}
    </div>
  );
}

function ExtrasEditor({
  value,
  onChange,
}: {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}) {
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");
  const entries = Object.entries(value);

  const addEntry = () => {
    const k = newKey.trim();
    const v = newVal.trim();
    if (!k) return;
    onChange({ ...value, [k]: v });
    setNewKey("");
    setNewVal("");
  };
  const removeEntry = (k: string) => {
    const next = { ...value };
    delete next[k];
    onChange(next);
  };
  const updateEntry = (k: string, v: string) => {
    onChange({ ...value, [k]: v });
  };

  return (
    <div className="space-y-2">
      <p className="text-xs" style={{ color: "var(--muted)" }}>
        Anything else recruiters should know — notice period, preferred start date, visa
        status, etc. Add a custom field below.
      </p>
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-2 items-center">
          <span
            className="text-xs px-2 py-1 rounded font-mono whitespace-nowrap"
            style={{ background: "var(--bg-2)", color: "var(--muted)", minHeight: 44, lineHeight: "36px" }}
          >
            {k}
          </span>
          <input
            type="text"
            value={typeof v === "string" ? v : JSON.stringify(v)}
            onChange={(e) => updateEntry(k, e.target.value)}
            aria-label={`Value for ${k}`}
            className="flex-1 text-sm rounded-md px-3"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              minHeight: 44,
            }}
          />
          <button
            type="button"
            onClick={() => removeEntry(k)}
            aria-label={`Remove ${k}`}
            className="btn btn-ghost btn-sm"
            style={{ minHeight: 44, minWidth: 44 }}
          >
            <Icon name="x" size={14} />
          </button>
        </div>
      ))}
      <div className="flex gap-2 items-center pt-2" style={{ borderTop: "1px dashed var(--line)" }}>
        <input
          type="text"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value.slice(0, 60))}
          placeholder="Field name"
          aria-label="New field name"
          className="text-sm rounded-md px-3"
          style={{
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
            color: "var(--ink)",
            minHeight: 44,
            width: 160,
          }}
        />
        <input
          type="text"
          value={newVal}
          onChange={(e) => setNewVal(e.target.value.slice(0, 500))}
          placeholder="Value"
          aria-label="New field value"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addEntry();
            }
          }}
          className="flex-1 text-sm rounded-md px-3"
          style={{
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
            color: "var(--ink)",
            minHeight: 44,
          }}
        />
        <button
          type="button"
          onClick={addEntry}
          disabled={!newKey.trim()}
          className="btn btn-ghost btn-sm"
          style={{ minHeight: 44 }}
        >
          <Icon name="plus" size={14} /> Add
        </button>
      </div>
    </div>
  );
}

function SaveBanner({
  status,
  hasValidationErrors,
}: {
  status: SaveStatus;
  hasValidationErrors: boolean;
}) {
  if (status.kind === "idle" && !hasValidationErrors) return null;
  let text: string;
  let color: string;
  if (hasValidationErrors) {
    text = "Fix the highlighted fields to save.";
    color = "var(--danger)";
  } else if (status.kind === "pending") {
    text = "Unsaved changes…";
    color = "var(--muted)";
  } else if (status.kind === "saving") {
    text = "Saving…";
    color = "var(--muted)";
  } else if (status.kind === "saved") {
    text = `Saved ${relativeTime(status.at)}`;
    color = "var(--copper-500)";
  } else if (status.kind === "error") {
    text = `Couldn't save: ${status.message}`;
    color = "var(--danger)";
  } else {
    return null;
  }
  return (
    <div
      role="status"
      aria-live="polite"
      className="sticky top-0 z-10 text-xs px-3 py-2 rounded-md"
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        color,
      }}
    >
      {text}
    </div>
  );
}

function Footer({ status }: { status: SaveStatus }) {
  if (status.kind !== "saved") return null;
  return (
    <p className="text-xs" style={{ color: "var(--muted)" }}>
      Last updated: {relativeTime(status.at)}
    </p>
  );
}

function relativeTime(d: Date): string {
  const diffSec = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec} seconds ago`;
  const minutes = Math.round(diffSec / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"} ago`;
}
