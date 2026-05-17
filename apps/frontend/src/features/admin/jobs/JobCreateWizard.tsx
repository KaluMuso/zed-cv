"use client";

import { useCallback, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { AdminJobCreatePayload } from "./types";
import { useDraftPersistence } from "./useDraftPersistence";
import { StepBasicInfo, step1Schema } from "./steps/StepBasicInfo";
import { StepCompensation, step2Schema } from "./steps/StepCompensation";
import { StepPlaceholder } from "./steps/StepPlaceholder";

// Total steps lives in one place so the indicator + bounds checks stay
// in sync as future PRs replace placeholders with real forms.
const TOTAL_STEPS = 5 as const;
type StepNumber = 1 | 2 | 3 | 4 | 5;

const STEP_LABELS: Record<StepNumber, string> = {
  1: "Basic info",
  2: "Compensation",
  3: "Role details",
  4: "Application",
  5: "Company context",
};

// Steps that ship with real form UI in this PR. Steps not in this set
// render the placeholder and cannot be navigated to via the progress
// indicator — they're reachable only via Next from the previous step
// (which is disabled, so effectively unreachable).
const IMPLEMENTED_STEPS: ReadonlySet<StepNumber> = new Set<StepNumber>([1, 2]);

// Initial form shape. source is always "manual" for wizard-created
// jobs; everything else is unset and gets filled in by the steps.
const EMPTY_FORM: Partial<AdminJobCreatePayload> = {
  source: "manual",
};

// Flatten a ZodError into a per-field message map. Only the first error
// per path is kept (matches the inline-error UI which renders one line
// per field).
function flattenZodErrors<T>(
  result: z.SafeParseReturnType<unknown, T>,
): Record<string, string> {
  if (result.success) return {};
  const out: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = issue.path[0];
    if (typeof key !== "string") continue;
    if (out[key]) continue;
    out[key] = issue.message;
  }
  return out;
}

export function JobCreateWizard() {
  const { initialDraft, queueWrite, clearDraft: _clearDraft } =
    useDraftPersistence();

  // Merge the saved draft (if any) over the empty template. We don't
  // re-write it on first render; the user's next keystroke triggers a
  // debounced write.
  const [data, setData] = useState<Partial<AdminJobCreatePayload>>(() => ({
    ...EMPTY_FORM,
    ...(initialDraft ?? {}),
  }));

  const [step, setStep] = useState<StepNumber>(1);

  // Step 1 errors are dampened — we don't show them until the user has
  // attempted to advance. Otherwise the form would light up red on
  // initial mount with "Title is required" on every field. Once flipped
  // true, errors show inline for any further keystrokes on that step.
  const [showStep1Errors, setShowStep1Errors] = useState<boolean>(false);

  // Step 2 errors are live (Next is locked in PR 3 — the only feedback
  // channel is inline rendering as the user types). This is also why
  // step 2 doesn't need a "show errors" gate.

  // Cheap aria-live channel: when Next is clicked with errors we set
  // this and the SR reads it once. Cleared on successful advance.
  const [liveMessage, setLiveMessage] = useState<string>("");

  // PR 4 will call analytics on mount + step change. The helper doesn't
  // exist yet (no client analytics surface present in the codebase).
  // TODO(PR4): emit "admin_job_wizard_started" on mount and
  // "admin_job_wizard_step_changed" on every step transition with
  // { from_step, to_step }. Defer until the analytics helper lands.

  const updateField = useCallback(
    <K extends keyof AdminJobCreatePayload>(
      field: K,
      value: AdminJobCreatePayload[K] | undefined,
    ) => {
      setData((prev) => {
        const next: Partial<AdminJobCreatePayload> = { ...prev };
        if (value === undefined) {
          delete next[field];
        } else {
          next[field] = value;
        }
        queueWrite(next);
        return next;
      });
    },
    [queueWrite],
  );

  // Live-compute per-step errors. Cheap (~7 zod checks per render); the
  // alternative — re-validate on a stale snapshot stored in state —
  // forces an extra render pass on every keystroke and is fiddlier.
  const step1ParseResult = useMemo(
    () =>
      step1Schema.safeParse({
        title: data.title,
        company: data.company,
        location: data.location,
        employment_type: data.employment_type,
        work_arrangement: data.work_arrangement,
        hybrid_days_per_week: data.hybrid_days_per_week,
      }),
    [
      data.title,
      data.company,
      data.location,
      data.employment_type,
      data.work_arrangement,
      data.hybrid_days_per_week,
    ],
  );

  const step2ParseResult = useMemo(
    () =>
      step2Schema.safeParse({
        salary_min: data.salary_min,
        salary_max: data.salary_max,
        currency: data.currency,
        pay_frequency: data.pay_frequency,
        bonus_structure: data.bonus_structure,
        equity_offered: data.equity_offered,
        benefits: data.benefits,
      }),
    [
      data.salary_min,
      data.salary_max,
      data.currency,
      data.pay_frequency,
      data.bonus_structure,
      data.equity_offered,
      data.benefits,
    ],
  );

  const step1Valid = step1ParseResult.success;
  const step1Errors = showStep1Errors
    ? flattenZodErrors(step1ParseResult)
    : {};
  const step2Errors = flattenZodErrors(step2ParseResult);

  const goToStep = useCallback(
    (target: StepNumber) => {
      setStep(target);
      setLiveMessage("");
    },
    [],
  );

  const onBack = useCallback(() => {
    if (step <= 1) return;
    goToStep((step - 1) as StepNumber);
  }, [step, goToStep]);

  const onNext = useCallback(() => {
    // Step 2 is locked: Next is disabled and PR 4 builds the rest of
    // the wizard before submit ships. Defensive guard so a stray
    // keyboard event can't force-advance.
    if (step === 2) return;
    if (step >= TOTAL_STEPS) return;

    if (step === 1) {
      setShowStep1Errors(true);
      if (!step1Valid) {
        setLiveMessage(
          "Step 1 has errors. Fix the highlighted fields to continue.",
        );
        return;
      }
    }
    goToStep((step + 1) as StepNumber);
  }, [step, step1Valid, goToStep]);

  const onProgressClick = useCallback(
    (target: StepNumber) => {
      if (target === step) return;
      // Only implemented steps are clickable. PR 4 will widen this.
      if (!IMPLEMENTED_STEPS.has(target)) return;
      goToStep(target);
    },
    [step, goToStep],
  );

  return (
    <div className="flex flex-col gap-6">
      {/* SR-only aria-live channel for validation errors. The visible
          error messages render inline below each field. */}
      <div role="status" aria-live="polite" className="sr-only">
        {liveMessage}
      </div>

      <ProgressIndicator
        current={step}
        onClick={onProgressClick}
      />

      <Card>
        <CardHeader>
          {/* h2 (not CardTitle) so semantic heading hierarchy is intact:
              the page renders h1 "Create a job" and this is its child
              section. CardTitle is a styled div, which would force AT
              users to grep visually for the step boundary. */}
          <h2 className="font-heading text-base leading-snug font-medium">
            Step {step} of {TOTAL_STEPS} — {STEP_LABELS[step]}
          </h2>
        </CardHeader>
        <CardContent>
          {step === 1 && (
            <StepBasicInfo
              data={data}
              errors={step1Errors}
              onChange={updateField}
            />
          )}
          {step === 2 && (
            <StepCompensation
              data={data}
              errors={step2Errors}
              onChange={updateField}
            />
          )}
          {step === 3 && (
            <StepPlaceholder stepNumber={3} title={STEP_LABELS[3]} />
          )}
          {step === 4 && (
            <StepPlaceholder stepNumber={4} title={STEP_LABELS[4]} />
          )}
          {step === 5 && (
            <StepPlaceholder stepNumber={5} title={STEP_LABELS[5]} />
          )}
        </CardContent>
      </Card>

      <NavRow
        step={step}
        step1Valid={step1Valid}
        onBack={onBack}
        onNext={onNext}
      />
    </div>
  );
}

// ── ProgressIndicator ────────────────────────────────────────────────
// Pill-shaped dots showing the active + reachable steps. Implemented
// steps are buttons (clickable); placeholder steps render as disabled
// spans so AT users get the same "you can't jump there yet" signal as
// sighted users.

function ProgressIndicator({
  current,
  onClick,
}: {
  current: StepNumber;
  onClick: (target: StepNumber) => void;
}) {
  return (
    <ol
      className="flex flex-wrap items-center gap-2"
      aria-label="Wizard progress"
    >
      {([1, 2, 3, 4, 5] as StepNumber[]).map((n) => {
        const isActive = n === current;
        const isReachable = IMPLEMENTED_STEPS.has(n);
        const label = `Step ${n}: ${STEP_LABELS[n]}`;
        const classes = cn(
          "inline-flex h-9 min-h-9 min-w-9 items-center justify-center rounded-full px-3 text-sm font-medium tabular-nums transition-colors",
          isActive && "bg-primary text-primary-foreground",
          !isActive && isReachable &&
            "bg-muted text-foreground hover:bg-muted/80 cursor-pointer",
          !isReachable && "bg-muted/40 text-muted-foreground cursor-not-allowed",
        );
        return (
          <li key={n}>
            {isReachable ? (
              <button
                type="button"
                aria-label={label}
                aria-current={isActive ? "step" : undefined}
                className={classes}
                onClick={() => onClick(n)}
              >
                {n}
              </button>
            ) : (
              <span
                aria-label={`${label} (locked)`}
                aria-disabled="true"
                className={classes}
              >
                {n}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

// ── NavRow ───────────────────────────────────────────────────────────
// Back is hidden on step 1 to remove a permanently-disabled control.
// On step 5 there's no Next at all.

function NavRow({
  step,
  step1Valid,
  onBack,
  onNext,
}: {
  step: StepNumber;
  step1Valid: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  const showBack = step > 1;
  const showNext = step < TOTAL_STEPS;

  // Step 2's Next is intentionally disabled — the remaining steps
  // ship in PR 4. Render with help text instead of hiding so the user
  // sees the wizard isn't broken.
  const isLockedStep = step === 2;

  let nextDisabled = false;
  if (step === 1) nextDisabled = !step1Valid;
  if (isLockedStep) nextDisabled = true;

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div>
        {showBack && (
          <Button
            type="button"
            variant="outline"
            size="lg"
            className="min-h-11"
            onClick={onBack}
          >
            <ChevronLeft />
            <span>Back</span>
          </Button>
        )}
      </div>
      <div className="flex flex-col items-end gap-1">
        {showNext && (
          <Button
            type="button"
            size="lg"
            className="min-h-11"
            disabled={nextDisabled}
            onClick={onNext}
          >
            <span>Next</span>
            <ChevronRight />
          </Button>
        )}
        {isLockedStep && (
          <p className="text-xs text-muted-foreground">
            Continue building in the next PR
          </p>
        )}
      </div>
    </div>
  );
}
