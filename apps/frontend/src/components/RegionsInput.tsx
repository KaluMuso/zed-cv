"use client";

/**
 * Acceptable-regions input for the Preferences tab.
 *
 * Pre-seeds the autocomplete with Zambian provinces + cities + the
 * 'International' / 'Remote' options so users with a wider scope can
 * declare it without typing the whole string. Free-form entries are
 * accepted — the suggestions are help, not a constraint.
 */
import { TagInput } from "@/components/TagInput";

// Provinces first (broader scope), then a small set of major cities,
// then non-geographic markers. Order matches what feels natural in
// the dropdown — broader-first.
const ZAMBIA_REGIONS = [
  "Lusaka",
  "Copperbelt",
  "Central",
  "Eastern",
  "Northern",
  "Luapula",
  "Muchinga",
  "North-Western",
  "Southern",
  "Western",
  // Major cities (for users who think city-first rather than province).
  "Ndola",
  "Kitwe",
  "Livingstone",
  "Kabwe",
  "Solwezi",
  "Chipata",
  // Non-geographic markers.
  "Remote (Zambia)",
  "Remote (Anywhere)",
  "International",
] as const;

interface RegionsInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  max?: number;
  disabled?: boolean;
}

export function RegionsInput({ value, onChange, max = 6, disabled }: RegionsInputProps) {
  return (
    <TagInput
      value={value}
      onChange={onChange}
      suggestions={ZAMBIA_REGIONS}
      placeholder="Add a region (e.g. Lusaka)"
      max={max}
      inputId="acceptable-regions-input"
      ariaLabel="Acceptable regions"
      disabled={disabled}
    />
  );
}
