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
  icon: "briefcase" | "bookmark" | "clock" | "star" | "map" | "user";
}[] = [
  { id: "all", label: "All jobs", icon: "briefcase" },
  { id: "saved", label: "Saved", icon: "bookmark" },
  { id: "closing", label: "Closing soon", icon: "clock" },
  { id: "with_salary", label: "With salary", icon: "star" },
  { id: "remote", label: "Remote", icon: "map" },
  { id: "full_time", label: "Full-time", icon: "user" },
];

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
      className="rounded-xl border p-2 lg:sticky lg:top-24"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
      aria-label="Job list filters"
    >
      <ul className="space-y-0.5">
        {PRESETS.map((item) => {
          const isActive = active === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onChange(item.id)}
                className={cn(
                  "w-full flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm text-left transition-colors",
                  isActive ? "font-medium" : "font-normal",
                )}
                style={{
                  background: isActive ? "var(--green-50)" : "transparent",
                  color: isActive ? "var(--green-700)" : "var(--ink-2)",
                }}
                aria-current={isActive ? "true" : undefined}
              >
                <Icon name={item.icon} size={16} className="shrink-0 opacity-80" />
                <span className="flex-1">{item.label}</span>
                {item.id === "saved" && savedCount != null && savedCount > 0 ? (
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded-full"
                    style={{ background: "var(--bg-2)", color: "var(--muted)" }}
                  >
                    {savedCount}
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
