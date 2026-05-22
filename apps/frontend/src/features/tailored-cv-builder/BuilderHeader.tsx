"use client";

import { cn } from "@/lib/utils";
import { BUILDER_STEPS, BUILDER_STEP_LABELS, type BuilderStep } from "./types";

export function BuilderHeader({
  currentStep,
  onStepClick,
}: {
  currentStep: BuilderStep;
  onStepClick?: (step: BuilderStep) => void;
}) {
  const currentIndex = BUILDER_STEPS.indexOf(currentStep);

  return (
    <header className="space-y-5 mb-6 sm:mb-8">
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight" style={{ color: "var(--ink)" }}>
        Build your{" "}
        <span className="font-display italic text-[1.05em]" style={{ color: "var(--copper-500, #b8602a)" }}>
          tailored
        </span>{" "}
        CV
      </h1>

      <nav aria-label="CV builder progress" className="overflow-x-auto pb-1 -mx-1 px-1">
        <ol className="flex items-center gap-1 sm:gap-2 min-w-max">
          {BUILDER_STEPS.map((step, index) => {
            const done = index < currentIndex;
            const active = step === currentStep;
            const upcoming = index > currentIndex;
            return (
              <li key={step} className="flex items-center gap-1 sm:gap-2">
                {index > 0 && (
                  <span
                    className="hidden sm:inline w-4 h-px shrink-0"
                    style={{ background: done ? "var(--copper-500, #b8602a)" : "var(--line-2)" }}
                    aria-hidden
                  />
                )}
                <button
                  type="button"
                  onClick={() => onStepClick?.(step)}
                  disabled={!onStepClick}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs sm:text-sm transition-colors",
                    onStepClick ? "cursor-pointer hover:bg-[var(--bg-2)]" : "cursor-default",
                    active && "font-medium"
                  )}
                  style={{
                    color: active
                      ? "var(--ink)"
                      : done
                        ? "var(--ink-2)"
                        : "var(--muted)",
                    background: active ? "var(--bg-2)" : "transparent",
                    border: active ? "1px solid var(--line-2)" : "1px solid transparent",
                  }}
                  aria-current={active ? "step" : undefined}
                >
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-mono"
                    style={{
                      background: done || active ? "var(--brand-500, #0E5C3A)" : "var(--surface)",
                      color: done || active ? "#fff" : "var(--muted)",
                      border: upcoming ? "1px solid var(--line-2)" : "none",
                    }}
                  >
                    {done ? "✓" : index + 1}
                  </span>
                  <span className="whitespace-nowrap">{BUILDER_STEP_LABELS[step]}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
    </header>
  );
}
