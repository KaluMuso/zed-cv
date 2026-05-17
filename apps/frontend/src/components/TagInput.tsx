"use client";

/**
 * Generic tag-input with optional autocomplete + max-entries cap.
 *
 * Shared by TargetRolesInput and RegionsInput — both are tag bags with
 * an autocomplete dropdown. Kept generic so the two callers only differ
 * in their suggestion list and label.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";

interface TagInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  suggestions?: readonly string[];
  placeholder?: string;
  max: number;
  /** ARIA-friendly label association — visible label lives in parent. */
  inputId: string;
  /** Optional label tied to the input for screen readers. */
  ariaLabel?: string;
  disabled?: boolean;
}

export function TagInput({
  value,
  onChange,
  suggestions = [],
  placeholder = "Type and press Enter",
  max,
  inputId,
  ariaLabel,
  disabled = false,
}: TagInputProps) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredSuggestions = useMemo(() => {
    const lower = draft.trim().toLowerCase();
    const taken = new Set(value.map((v) => v.toLowerCase()));
    return suggestions
      .filter(
        (s) =>
          !taken.has(s.toLowerCase()) &&
          (!lower || s.toLowerCase().includes(lower)),
      )
      .slice(0, 8);
  }, [draft, suggestions, value]);

  const atMax = value.length >= max;

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (!trimmed || atMax) return;
    const key = trimmed.toLowerCase();
    if (value.some((v) => v.toLowerCase() === key)) return;
    onChange([...value, trimmed]);
    setDraft("");
    setOpen(false);
  };

  const removeTag = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  // Close the suggestion popover on outside click. Touch / mobile-safe
  // — pointerdown fires on iOS Safari where mousedown does not.
  useEffect(() => {
    if (!open) return;
    const handler = (e: PointerEvent) => {
      if (!inputRef.current?.parentElement?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handler);
    return () => document.removeEventListener("pointerdown", handler);
  }, [open]);

  return (
    <div className="relative">
      <div
        className="flex flex-wrap gap-2 p-2 rounded-md min-h-[44px]"
        style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
      >
        {value.map((tag, idx) => (
          <span
            key={`${tag}-${idx}`}
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs"
            style={{ background: "var(--bg-1)", border: "1px solid var(--line)" }}
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(idx)}
              aria-label={`Remove ${tag}`}
              disabled={disabled}
              className="inline-flex items-center justify-center"
              style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              <Icon name="x" size={12} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          id={inputId}
          aria-label={ariaLabel}
          type="text"
          value={draft}
          disabled={disabled || atMax}
          placeholder={atMax ? `Maximum ${max} entries` : placeholder}
          onChange={(e) => {
            setDraft(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addTag(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              removeTag(value.length - 1);
            }
          }}
          className="flex-1 min-w-[120px] text-sm"
          style={{
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--ink)",
            minHeight: 28,
          }}
        />
      </div>
      {open && filteredSuggestions.length > 0 && !atMax && (
        <ul
          role="listbox"
          className="absolute z-10 left-0 right-0 mt-1 rounded-md max-h-48 overflow-auto"
          style={{ background: "var(--bg-1)", border: "1px solid var(--line)" }}
        >
          {filteredSuggestions.map((s) => (
            <li key={s}>
              <button
                type="button"
                onClick={() => addTag(s)}
                className="w-full text-left px-3 py-2 text-sm"
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ink)" }}
                onMouseDown={(e) => e.preventDefault()}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div
        className="text-xs mt-1"
        style={{ color: "var(--muted)" }}
        aria-live="polite"
      >
        {value.length} / {max}
      </div>
    </div>
  );
}
