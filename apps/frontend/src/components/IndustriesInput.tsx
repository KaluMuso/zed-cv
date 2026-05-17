"use client";

/**
 * Repeatable industry-experience input.
 *
 * Each row is {industry: string, years_experience: int}. Caps at 8
 * entries (matches the API). years_experience is bounded 0-80.
 */
import { Icon } from "@/components/ui/Icon";
import type { IndustryExperience } from "@/lib/api";

// Common Zambian industries — mirrors the keyword classifier in
// apps/backend/app/services/preferences_auto_populate.py so the dropdown
// matches what auto-populate emits. Free-form input still works.
const COMMON_INDUSTRIES = [
  "Agriculture",
  "Mining",
  "Healthcare",
  "Government",
  "Banking",
  "Insurance",
  "NGO",
  "Education",
  "Telecommunications",
  "Technology",
  "Retail",
  "Hospitality",
  "Construction",
  "Engineering",
  "Consulting",
  "Logistics",
  "Manufacturing",
  "Tourism",
  "Energy",
  "Legal",
];

interface IndustriesInputProps {
  value: IndustryExperience[];
  onChange: (next: IndustryExperience[]) => void;
  max?: number;
  disabled?: boolean;
}

export function IndustriesInput({
  value,
  onChange,
  max = 8,
  disabled,
}: IndustriesInputProps) {
  const update = (idx: number, patch: Partial<IndustryExperience>) => {
    onChange(value.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  };
  const remove = (idx: number) => onChange(value.filter((_, i) => i !== idx));
  const add = () => {
    if (value.length >= max) return;
    onChange([...value, { industry: "", years_experience: 0 }]);
  };

  return (
    <div className="space-y-2">
      <datalist id="industries-suggestions">
        {COMMON_INDUSTRIES.map((i) => (
          <option key={i} value={i} />
        ))}
      </datalist>

      {value.map((row, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <input
            type="text"
            value={row.industry}
            onChange={(e) => update(idx, { industry: e.target.value })}
            placeholder="Industry"
            list="industries-suggestions"
            aria-label={`Industry ${idx + 1}`}
            disabled={disabled}
            className="flex-1 text-sm rounded-md px-3"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              minHeight: 44,
            }}
            maxLength={120}
          />
          <input
            type="number"
            min={0}
            max={80}
            step={1}
            value={row.years_experience}
            onChange={(e) => {
              // Strip non-integer / out-of-range input. The server
              // also clamps but a tighter client constraint stops
              // the user typing "0.5" and seeing a 422 on auto-save.
              const raw = e.target.value;
              const parsed = parseInt(raw, 10);
              const clamped = Math.max(0, Math.min(Number.isFinite(parsed) ? parsed : 0, 80));
              update(idx, { years_experience: clamped });
            }}
            aria-label={`Years of experience in ${row.industry || "industry " + (idx + 1)}`}
            disabled={disabled}
            className="text-sm rounded-md px-2"
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              color: "var(--ink)",
              minHeight: 44,
              width: 80,
            }}
          />
          <span className="text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
            yrs
          </span>
          <button
            type="button"
            onClick={() => remove(idx)}
            disabled={disabled}
            aria-label={`Remove ${row.industry || "industry " + (idx + 1)}`}
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
        <Icon name="plus" size={14} /> Add industry
      </button>
      <div className="text-xs" style={{ color: "var(--muted)" }} aria-live="polite">
        {value.length} / {max}
      </div>
    </div>
  );
}
