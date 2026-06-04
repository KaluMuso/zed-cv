"use client";

import { useCallback, useEffect, useId, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import { btnClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

const SESSION_KEY = "zedapply:jobs-mobile-filters-open";

function readStoredOpen(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return sessionStorage.getItem(SESSION_KEY) === "1";
  } catch {
    return false;
  }
}

function writeStoredOpen(open: boolean): void {
  try {
    sessionStorage.setItem(SESSION_KEY, open ? "1" : "0");
  } catch {
    /* private mode / quota */
  }
}

export function MobileFilterShell({
  activeFilterCount,
  onClearAll,
  showClosed,
  onShowClosedChange,
  children,
}: {
  activeFilterCount: number;
  onClearAll: () => void;
  showClosed: boolean;
  onShowClosedChange: (next: boolean) => void;
  children: ReactNode;
}) {
  const panelId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setIsOpen(readStoredOpen());
    setHydrated(true);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((prev) => {
      const next = !prev;
      writeStoredOpen(next);
      return next;
    });
  }, []);

  const label =
    activeFilterCount > 0
      ? `Filters · ${activeFilterCount} active`
      : "Filters";

  return (
    <div className="lg:hidden mb-4">
      <div
        className="flex items-center gap-2 rounded-lg border min-h-12 overflow-hidden"
        style={{ borderColor: "var(--line)", background: "var(--surface)" }}
      >
        <button
          type="button"
          className={cn(
            "flex flex-1 items-center gap-2 px-3 min-h-12",
            "text-sm font-medium transition-colors",
          )}
          style={{ color: "var(--ink)" }}
          onClick={toggle}
          aria-expanded={hydrated ? isOpen : false}
          aria-controls={panelId}
        >
          <Icon
            name="chevronDown"
            size={16}
            className={cn(
              "shrink-0 transition-transform duration-200 ease-out",
              isOpen ? "rotate-180" : "",
            )}
            aria-hidden
          />
          <span className="flex-1 text-left">{label}</span>
          {!isOpen ? (
            <Icon name="plus" size={16} className="shrink-0 opacity-60" aria-hidden />
          ) : null}
        </button>
        {isOpen ? (
          <button
            type="button"
            className={cn(btnClass("ghost", "sm"), "shrink-0 mr-2 text-xs")}
            onClick={onClearAll}
          >
            <Icon name="x" size={12} />
            Clear all
          </button>
        ) : null}
      </div>

      <div
        id={panelId}
        className={cn(
          "overflow-hidden transition-all duration-200 ease-out",
          isOpen ? "max-h-[480px] opacity-100 mt-2" : "max-h-0 opacity-0",
        )}
        hidden={hydrated ? !isOpen : true}
      >
        <div
          className="rounded-lg border p-3 space-y-3"
          style={{ borderColor: "var(--line)", background: "var(--surface)" }}
        >
          {children}
          <label
            className="flex items-center gap-2 text-xs pt-1 border-t"
            style={{ color: "var(--ink-2)", borderColor: "var(--line)" }}
          >
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-input"
              checked={showClosed}
              onChange={(e) => onShowClosedChange(e.target.checked)}
              aria-label="Show closed jobs"
            />
            Show closed
          </label>
        </div>
      </div>
    </div>
  );
}
