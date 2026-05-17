"use client";

/**
 * Repeatable language input for the Preferences tab.
 *
 * Each row is {language: string, proficiency: enum}. User can add up
 * to MAX rows (default 8 — matches the API cap). The proficiency
 * vocabulary matches user_preferences.languages, not CV-sections
 * languages — these are about self-rated everyday usage, not formal
 * fluency tests.
 */
import { Icon } from "@/components/ui/Icon";
import type {
  PreferredLanguage,
  PreferenceLanguageProficiency,
} from "@/lib/api";

const PROFICIENCY_OPTIONS: { value: PreferenceLanguageProficiency; label: string }[] = [
  { value: "native", label: "Native" },
  { value: "fluent", label: "Fluent" },
  { value: "intermediate", label: "Intermediate" },
  { value: "basic", label: "Basic" },
];

// Curated language suggestions for the input's datalist. Zambia-first
// with the big international ones tacked on. Free-form input is still
// allowed — the datalist is a hint, not a select.
const COMMON_LANGUAGES = [
  "English",
  "Bemba",
  "Nyanja",
  "Tonga",
  "Lozi",
  "Kaonde",
  "Lunda",
  "Luvale",
  "Tumbuka",
  "Swahili",
  "French",
  "Portuguese",
  "Mandarin",
];

interface LanguagesInputProps {
  value: PreferredLanguage[];
  onChange: (next: PreferredLanguage[]) => void;
  max?: number;
  disabled?: boolean;
}

export function LanguagesInput({ value, onChange, max = 8, disabled }: LanguagesInputProps) {
  const update = (idx: number, patch: Partial<PreferredLanguage>) => {
    onChange(value.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  };
  const remove = (idx: number) => onChange(value.filter((_, i) => i !== idx));
  const add = () => {
    if (value.length >= max) return;
    onChange([...value, { language: "", proficiency: "intermediate" }]);
  };

  return (
    <div className="space-y-2">
      <datalist id="languages-suggestions">
        {COMMON_LANGUAGES.map((l) => (
          <option key={l} value={l} />
        ))}
      </datalist>

      {value.map((row, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <input
            type="text"
            value={row.language}
            onChange={(e) => update(idx, { language: e.target.value })}
            placeholder="Language"
            list="languages-suggestions"
            aria-label={`Language ${idx + 1}`}
            disabled={disabled}
            className="flex-1 text-sm rounded-md px-3"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              minHeight: 44,
            }}
            maxLength={80}
          />
          <select
            value={row.proficiency}
            onChange={(e) =>
              update(idx, { proficiency: e.target.value as PreferenceLanguageProficiency })
            }
            aria-label={`Proficiency for ${row.language || "language " + (idx + 1)}`}
            disabled={disabled}
            className="text-sm rounded-md px-2"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              minHeight: 44,
            }}
          >
            {PROFICIENCY_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => remove(idx)}
            disabled={disabled}
            aria-label={`Remove ${row.language || "language " + (idx + 1)}`}
            className="btn btn-ghost btn-sm"
            style={{ minHeight: 44, minWidth: 44 }}
          >
            <Icon name="x" size={14} />
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={add}
        disabled={disabled || value.length >= max}
        className="btn btn-ghost btn-sm"
      >
        <Icon name="plus" size={14} /> Add language
      </button>
      <div className="text-xs" style={{ color: "var(--muted)" }} aria-live="polite">
        {value.length} / {max}
      </div>
    </div>
  );
}
