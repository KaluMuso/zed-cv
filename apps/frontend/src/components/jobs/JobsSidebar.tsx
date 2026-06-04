"use client";

import { cn } from "@/lib/utils";
import { Icon } from "@/components/ui/Icon";

export type JobsListPreset =
  | "all"
  | "saved"
  | "closing"
  | "with_salary"
  | "remote"
  | "full_time";

const PRESETS: {
  id: JobsListPreset;
  label: string;
  shortLabel: string;
  icon: "briefcase" | "bookmark" | "clock" | "star" | "map" | "user";
}[] = [
  { id: "all", label: "All jobs", shortLabel: "All", icon: "briefcase" },
  { id: "saved", label: "Saved", shortLabel: "Saved", icon: "bookmark" },
  { id: "closing", label: "Closing soon", shortLabel: "Closing", icon: "clock" },
  { id: "with_salary", label: "With salary", shortLabel: "Salary", icon: "star" },
  { id: "remote", label: "Remote", shortLabel: "Remote", icon: "map" },
  { id: "full_time", label: "Full-time", shortLabel: "Full-time", icon: "user" },
];

function PresetButton({
  item,
  isActive,
  onChange,
  savedCount,
  compact,
}: {
  item: (typeof PRESETS)[number];
  isActive: boolean;
  onChange: (preset: JobsListPreset) => void;
  savedCount?: number;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(item.id)}
      className={cn(
        "flex items-center gap-2 rounded-full px-3 py-2 text-sm transition-colors shrink-0",
        compact ? "whitespace-nowrap" : "w-full rounded-lg py-2.5 text-left",
        isActive ? "font-medium" : "font-normal",
      )}
      style={{
        background: isActive ? "var(--green-50)" : compact ? "var(--surface)" : "transparent",
        color: isActive ? "var(--green-700)" : "var(--ink-2)",
        border: compact ? "1px solid var(--line)" : "none",
      }}
      aria-current={isActive ? "true" : undefined}
    >
      <Icon name={item.icon} size={compact ? 14 : 16} className="shrink-0 opacity-80" />
      <span>{compact ? item.shortLabel : item.label}</span>
      {item.id === "saved" && savedCount != null && savedCount > 0 ? (
        <span
          className="text-[10px] font-mono px-1.5 py-0.5 rounded-full ml-auto"
          style={{ background: "var(--bg-2)", color: "var(--muted)" }}
        >
          {savedCount}
        </span>
      ) : null}
    </button>
  );
}

/** Desktop / tablet sidebar (lg+). */
export function JobsSidebar({
  active,
  onChange,
  savedCount,
}: {
  active: JobsListPreset;
  onChange: (preset: JobsListPreset) => void;
  savedCount?: number;
}) {
  return (
    <nav
      className="hidden lg:block rounded-xl border p-2 lg:sticky lg:top-24"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
      aria-label="Job list filters"
    >
      <ul className="space-y-0.5">
        {PRESETS.map((item) => (
          <li key={item.id}>
            <PresetButton
              item={item}
              isActive={active === item.id}
              onChange={onChange}
              savedCount={savedCount}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Preset chips — horizontal row or stacked grid inside MobileFilterShell. */
export function JobsSidebarMobile({
  active,
  onChange,
  savedCount,
  layout = "chips",
}: {
  active: JobsListPreset;
  onChange: (preset: JobsListPreset) => void;
  savedCount?: number;
  layout?: "chips" | "stack";
}) {
  const stacked = layout === "stack";

  return (
    <nav aria-label="Job list filters" className={stacked ? undefined : "-mx-1 px-1"}>
      <div
        className={
          stacked
            ? "grid grid-cols-2 gap-2 sm:grid-cols-3"
            : "flex gap-2 min-w-max overflow-x-auto scroll-thin pb-1"
        }
        style={stacked ? undefined : { scrollbarWidth: "thin" }}
      >
        {PRESETS.map((item) => (
          <PresetButton
            key={item.id}
            item={item}
            isActive={active === item.id}
            onChange={onChange}
            savedCount={savedCount}
            compact={!stacked}
          />
        ))}
      </div>
    </nav>
  );
}
