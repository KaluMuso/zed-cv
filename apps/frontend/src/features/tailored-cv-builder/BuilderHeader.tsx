"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/ui/Icon";
import { BUILDER_STEPS, BUILDER_STEP_LABELS, type BuilderStep } from "./types";

export function BuilderHeader({
  currentStep,
  onStepClick,
  jobTitle,
  company,
}: {
  currentStep: BuilderStep;
  onStepClick?: (step: BuilderStep) => void;
  jobTitle?: string | null;
  company?: string | null;
}) {
  const currentIndex = BUILDER_STEPS.indexOf(currentStep);
  const hasJobContext = Boolean(jobTitle?.trim());

  return (
    <header className="space-y-4 mb-6 sm:mb-8">
      <Link
        href="/matches"
        className="inline-flex items-center gap-1.5 text-sm font-medium hover:underline"
        style={{ color: "var(--muted)" }}
      >
        <Icon name="arrowLeft" size={14} />
        Back to site
      </Link>

      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight" style={{ color: "var(--ink)" }}>
        {hasJobContext ? (
          <>
            Tailored CV for{" "}
            <span className="font-display italic" style={{ color: "var(--green-700)" }}>
              {jobTitle}
            </span>
            {company?.trim() ? (
              <>
                {" "}
                at <span style={{ color: "var(--ink-2)" }}>{company}</span>
              </>
            ) : null}
          </>
        ) : (
          <>
            Build your{" "}
            <span className="font-display italic" style={{ color: "var(--green-700)" }}>
              tailored
            </span>{" "}
            CV
          </>
        )}
      </h1>

      <nav
        aria-label="CV builder progress"
        className="overflow-x-auto pb-0 -mx-1 px-1 border-b"
        style={{ borderColor: "var(--line)" }}
      >
        <ol className="flex items-center gap-0 min-w-max">
          {BUILDER_STEPS.map((step, index) => {
            const done = index < currentIndex;
            const active = step === currentStep;
            return (
              <li key={step}>
                <button
                  type="button"
                  onClick={() => onStepClick?.(step)}
                  disabled={!onStepClick}
                  className={cn(
                    "relative px-3 sm:px-4 py-2.5 text-xs sm:text-sm whitespace-nowrap transition-colors",
                    onStepClick ? "cursor-pointer hover:text-[var(--ink)]" : "cursor-default",
                    active ? "font-semibold" : "font-medium",
                  )}
                  style={{
                    color: active ? "var(--green-700)" : done ? "var(--ink-2)" : "var(--muted)",
                    background: "transparent",
                    border: "none",
                  }}
                  aria-current={active ? "step" : undefined}
                >
                  {BUILDER_STEP_LABELS[step]}
                  {active && (
                    <span
                      className="absolute left-2 right-2 sm:left-3 sm:right-3 bottom-0 h-0.5 rounded-full"
                      style={{ background: "var(--green-700)" }}
                      aria-hidden
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
    </header>
  );
}
