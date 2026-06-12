"use client";

import {
  type IndustryExperience,
  type JobPreferences,
  type JobSalaryFrequency,
  type PreferredLanguage,
  type PreferredWorkArrangement,
} from "@/lib/api";
import { LanguagesInput } from "@/components/LanguagesInput";
import { IndustriesInput } from "@/components/IndustriesInput";
import { RegionsInput } from "@/components/RegionsInput";
import {
  EDUCATION_LEVEL_OPTIONS,
  NOTICE_PERIOD_OPTIONS,
  PREFERENCE_FIELD_CLASS,
  preferenceFieldStyle,
} from "./constants";

export function YearsExperienceField({
  value,
  onChange,
  onBlur,
}: {
  value: number;
  onChange: (years: number) => void;
  onBlur?: () => void;
}) {
  return (
    <label className="text-xs block" style={{ color: "var(--muted)" }}>
      Years of experience
      <input
        type="number"
        min={0}
        max={60}
        value={value}
        onChange={(e) => {
          const parsed = parseInt(e.target.value, 10);
          onChange(Number.isFinite(parsed) && parsed >= 0 ? parsed : 0);
        }}
        onBlur={onBlur}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      />
    </label>
  );
}

export function EducationLevelField({
  value,
  onChange,
}: {
  value: string;
  onChange: (level: string) => void;
}) {
  return (
    <label htmlFor="education-level-select" className="text-xs block" style={{ color: "var(--muted)" }}>
      Highest qualification
      <select
        id="education-level-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      >
        <option value="">Not specified</option>
        {EDUCATION_LEVEL_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function NoticePeriodField({
  value,
  onChange,
}: {
  value: string;
  onChange: (period: string) => void;
}) {
  return (
    <label htmlFor="notice-period-select" className="text-xs block" style={{ color: "var(--muted)" }}>
      Notice period
      <select
        id="notice-period-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      >
        <option value="">Not specified</option>
        {NOTICE_PERIOD_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function WorkArrangementField({
  value,
  onChange,
}: {
  value: PreferredWorkArrangement | null;
  onChange: (value: PreferredWorkArrangement | null) => void;
}) {
  return (
    <label htmlFor="work-arrangement-select" className="text-xs block" style={{ color: "var(--muted)" }}>
      Preferred arrangement
      <select
        id="work-arrangement-select"
        value={value ?? ""}
        onChange={(e) =>
          onChange((e.target.value || null) as PreferredWorkArrangement | null)
        }
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      >
        <option value="">Not specified</option>
        <option value="remote">Remote</option>
        <option value="hybrid">Hybrid</option>
        <option value="onsite">On-site</option>
        <option value="any">Any</option>
      </select>
    </label>
  );
}

export function EmploymentTypeField({
  value,
  onChange,
}: {
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const options = [
    { value: "full_time", label: "Full-time" },
    { value: "part_time", label: "Part-time" },
    { value: "contract", label: "Contract" },
    { value: "freelance", label: "Freelance" },
    { value: "internship", label: "Internship" },
    { value: "temporary", label: "Temporary" },
  ];

  const handleToggle = (optValue: string) => {
    if (value.includes(optValue)) {
      onChange(value.filter((v) => v !== optValue));
    } else {
      onChange([...value, optValue]);
    }
  };

  return (
    <div className="text-xs flex flex-col gap-2" style={{ color: "var(--muted)" }}>
      <span>Preferred employment types</span>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const checked = value.includes(opt.value);
          return (
            <label
              key={opt.value}
              className="inline-flex items-center gap-1 cursor-pointer"
              style={{ color: "var(--ink)" }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => handleToggle(opt.value)}
                style={{ width: 16, height: 16 }}
              />
              {opt.label}
            </label>
          );
        })}
      </div>
    </div>
  );
}

export function RelocateField({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="text-xs flex flex-col gap-1" style={{ color: "var(--muted)" }}>
      <span>Willing to relocate</span>
      <span className="inline-flex items-center gap-2 mt-1">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          aria-label="Willing to relocate"
          style={{ width: 20, height: 20 }}
        />
        <span className="text-sm" style={{ color: "var(--ink)" }}>
          {checked ? "Yes" : "No"}
        </span>
      </span>
    </label>
  );
}

export function RegionsField({
  value,
  onChange,
}: {
  value: string[];
  onChange: (regions: string[]) => void;
}) {
  return (
    <div>
      <label
        htmlFor="acceptable-regions-input"
        className="block text-xs mb-2"
        style={{ color: "var(--muted)" }}
      >
        Regions you&apos;d work in. Up to 6.
      </label>
      <RegionsInput value={value} onChange={onChange} />
    </div>
  );
}

export function LanguagesField({
  value,
  onChange,
}: {
  value: PreferredLanguage[];
  onChange: (langs: PreferredLanguage[]) => void;
}) {
  return (
    <div>
      <div className="text-xs mb-2" style={{ color: "var(--muted)" }}>
        Languages you speak (up to 8)
      </div>
      <LanguagesInput value={value} onChange={onChange} />
    </div>
  );
}

export function IndustriesField({
  value,
  onChange,
}: {
  value: IndustryExperience[];
  onChange: (inds: IndustryExperience[]) => void;
}) {
  return (
    <div>
      <div className="text-xs mb-2" style={{ color: "var(--muted)" }}>
        Industries you&apos;ve worked in (up to 8)
      </div>
      <IndustriesInput value={value} onChange={onChange} />
    </div>
  );
}

export function SalaryExpectationsFields({
  preferences,
  onChange,
  salaryError,
}: {
  preferences: JobPreferences;
  onChange: (patch: {
    salary_min?: number | null;
    salary_max?: number | null;
    salary_frequency?: JobSalaryFrequency | null;
    salary_currency?: string;
  }) => void;
  salaryError?: string | null;
}) {
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <SalaryKwachaField
          id="salary-min"
          label="Minimum"
          valueNgwee={preferences.salary_min}
          onChange={(v) => onChange({ salary_min: v })}
        />
        <SalaryKwachaField
          id="salary-max"
          label="Maximum"
          valueNgwee={preferences.salary_max}
          onChange={(v) => onChange({ salary_max: v })}
        />
      </div>
      {salaryError ? (
        <p className="text-xs mt-2" style={{ color: "var(--danger)" }} aria-live="polite">
          {salaryError}
        </p>
      ) : null}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
        <label className="text-xs" style={{ color: "var(--muted)" }}>
          Frequency
          <select
            value={preferences.salary_frequency ?? ""}
            onChange={(e) =>
              onChange({
                salary_frequency: (e.target.value || null) as JobSalaryFrequency | null,
              })
            }
            className={PREFERENCE_FIELD_CLASS}
            style={preferenceFieldStyle}
          >
            <option value="">Not specified</option>
            <option value="monthly">Monthly</option>
            <option value="annual">Annual</option>
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
          </select>
        </label>
        <label className="text-xs" style={{ color: "var(--muted)" }}>
          Currency
          <input
            type="text"
            value={preferences.salary_currency}
            onChange={(e) =>
              onChange({ salary_currency: e.target.value.toUpperCase().slice(0, 3) })
            }
            maxLength={3}
            minLength={3}
            className={`${PREFERENCE_FIELD_CLASS} font-mono`}
            style={preferenceFieldStyle}
          />
        </label>
      </div>
      <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
        Amounts in kwacha (K). Leave blank if you&apos;d rather not say.
      </p>
    </>
  );
}

function SalaryKwachaField({
  id,
  label,
  valueNgwee,
  onChange,
}: {
  id: string;
  label: string;
  valueNgwee: number | null;
  onChange: (v: number | null) => void;
}) {
  const valueKwacha = valueNgwee === null ? "" : (valueNgwee / 100).toString();
  return (
    <label htmlFor={id} className="text-xs" style={{ color: "var(--muted)" }}>
      {label} (K)
      <input
        id={id}
        type="number"
        min={0}
        step={50}
        value={valueKwacha}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
            return;
          }
          const parsed = parseFloat(raw);
          if (!Number.isFinite(parsed) || parsed < 0) {
            onChange(null);
            return;
          }
          onChange(Math.round(parsed * 100));
        }}
        className={PREFERENCE_FIELD_CLASS}
        style={preferenceFieldStyle}
      />
    </label>
  );
}

export function validateSalaryRange(
  salaryMin: number | null,
  salaryMax: number | null,
): string | null {
  if (
    salaryMin !== null &&
    salaryMax !== null &&
    salaryMin > salaryMax
  ) {
    return "Minimum can't be more than maximum.";
  }
  return null;
}
