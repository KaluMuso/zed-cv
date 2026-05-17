"use client";

import { z } from "zod";
import { X, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import type { AdminJobCreatePayload } from "../types";
import {
  BENEFITS_MAX_ITEMS,
  BENEFIT_MAX_LENGTH,
  BONUS_STRUCTURE_MAX_LENGTH,
  CURRENCIES,
  PAY_FREQUENCIES,
} from "../job-enums";

// Backend treats every compensation field as optional. We accept empty
// strings, undefined, and nulls; salary fields normalise to integer
// ngwee (the wizard passes raw numbers — PR 4's submit step is what
// converts ZMW → ngwee if the form ships kwacha).
export const step2Schema = z
  .object({
    salary_min: z.number().int().min(0).nullable().optional(),
    salary_max: z.number().int().min(0).nullable().optional(),
    currency: z
      .string()
      .trim()
      .length(3)
      .toUpperCase()
      .nullable()
      .optional(),
    pay_frequency: z
      .enum(["monthly", "annual", "hourly", "daily"])
      .nullable()
      .optional(),
    bonus_structure: z
      .string()
      .trim()
      .max(BONUS_STRUCTURE_MAX_LENGTH)
      .nullable()
      .optional(),
    equity_offered: z.boolean().nullable().optional(),
    benefits: z
      .array(
        z.string().trim().min(1).max(BENEFIT_MAX_LENGTH),
      )
      .max(BENEFITS_MAX_ITEMS)
      .nullable()
      .optional(),
  })
  .superRefine((val, ctx) => {
    if (
      val.salary_min != null &&
      val.salary_max != null &&
      val.salary_max < val.salary_min
    ) {
      ctx.addIssue({
        code: "custom",
        path: ["salary_max"],
        message: "Maximum must be greater than or equal to minimum",
      });
    }
  });

export type Step2Data = z.infer<typeof step2Schema>;

type FieldErrors = Partial<Record<keyof Step2Data, string | undefined>>;

export type StepCompensationProps = {
  data: Partial<AdminJobCreatePayload>;
  errors: FieldErrors;
  onChange: <K extends keyof AdminJobCreatePayload>(
    field: K,
    value: AdminJobCreatePayload[K] | undefined,
  ) => void;
};

const SELECT_CLASS =
  "h-11 min-h-11 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50";

const TEXTAREA_CLASS =
  "min-h-[88px] w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20";

const LABEL_CLASS = "text-sm font-medium leading-none text-foreground";

const ERROR_CLASS = "text-xs text-destructive";

// Coerce <input type="number"> value to a number-or-null. Empty string
// becomes null so optional salary fields can be cleared.
function toNumberOrNull(raw: string): number | null {
  if (raw === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function StepCompensation({
  data,
  errors,
  onChange,
}: StepCompensationProps) {
  const salaryMinId = "step2-salary-min";
  const salaryMaxId = "step2-salary-max";
  const currencyId = "step2-currency";
  const frequencyId = "step2-pay-frequency";
  const bonusId = "step2-bonus";
  const equityId = "step2-equity";

  // Local view of benefits — backed by data.benefits with a guaranteed
  // array (the form stores null when unset, but UI needs []).
  const benefits = data.benefits ?? [];
  const canAddBenefit = benefits.length < BENEFITS_MAX_ITEMS;

  const updateBenefit = (index: number, next: string) => {
    const out = [...benefits];
    out[index] = next;
    onChange("benefits", out);
  };

  const addBenefit = () => {
    if (!canAddBenefit) return;
    onChange("benefits", [...benefits, ""]);
  };

  const removeBenefit = (index: number) => {
    const out = benefits.filter((_, i) => i !== index);
    onChange("benefits", out.length === 0 ? null : out);
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-1.5">
        <label htmlFor={salaryMinId} className={LABEL_CLASS}>
          Salary minimum
        </label>
        <Input
          id={salaryMinId}
          type="number"
          min={0}
          className="min-h-11"
          placeholder="e.g. 5000"
          value={data.salary_min ?? ""}
          onChange={(e) =>
            onChange("salary_min", toNumberOrNull(e.target.value))
          }
          aria-invalid={errors.salary_min ? "true" : undefined}
          aria-describedby={
            errors.salary_min ? `${salaryMinId}-error` : undefined
          }
        />
        {errors.salary_min && (
          <p id={`${salaryMinId}-error`} className={ERROR_CLASS}>
            {errors.salary_min}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={salaryMaxId} className={LABEL_CLASS}>
          Salary maximum
        </label>
        <Input
          id={salaryMaxId}
          type="number"
          min={0}
          className="min-h-11"
          placeholder="e.g. 8000"
          value={data.salary_max ?? ""}
          onChange={(e) =>
            onChange("salary_max", toNumberOrNull(e.target.value))
          }
          aria-invalid={errors.salary_max ? "true" : undefined}
          aria-describedby={
            errors.salary_max ? `${salaryMaxId}-error` : undefined
          }
        />
        {errors.salary_max && (
          <p id={`${salaryMaxId}-error`} className={ERROR_CLASS}>
            {errors.salary_max}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={currencyId} className={LABEL_CLASS}>
          Currency
        </label>
        <select
          id={currencyId}
          className={SELECT_CLASS}
          value={data.currency ?? "ZMW"}
          onChange={(e) =>
            onChange("currency", e.target.value || null)
          }
          aria-invalid={errors.currency ? "true" : undefined}
          aria-describedby={
            errors.currency ? `${currencyId}-error` : undefined
          }
        >
          {CURRENCIES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.currency && (
          <p id={`${currencyId}-error`} className={ERROR_CLASS}>
            {errors.currency}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={frequencyId} className={LABEL_CLASS}>
          Pay frequency
        </label>
        <select
          id={frequencyId}
          className={SELECT_CLASS}
          value={data.pay_frequency ?? "monthly"}
          onChange={(e) =>
            onChange(
              "pay_frequency",
              (e.target.value as AdminJobCreatePayload["pay_frequency"]) ??
                null,
            )
          }
          aria-invalid={errors.pay_frequency ? "true" : undefined}
          aria-describedby={
            errors.pay_frequency ? `${frequencyId}-error` : undefined
          }
        >
          {PAY_FREQUENCIES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.pay_frequency && (
          <p id={`${frequencyId}-error`} className={ERROR_CLASS}>
            {errors.pay_frequency}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <label htmlFor={bonusId} className={LABEL_CLASS}>
          Bonus structure
        </label>
        <textarea
          id={bonusId}
          className={TEXTAREA_CLASS}
          rows={3}
          maxLength={BONUS_STRUCTURE_MAX_LENGTH}
          placeholder="e.g. Annual performance bonus up to 15% of salary"
          value={data.bonus_structure ?? ""}
          onChange={(e) =>
            onChange("bonus_structure", e.target.value || null)
          }
          aria-invalid={errors.bonus_structure ? "true" : undefined}
          aria-describedby={
            errors.bonus_structure ? `${bonusId}-error` : undefined
          }
        />
        {errors.bonus_structure && (
          <p id={`${bonusId}-error`} className={ERROR_CLASS}>
            {errors.bonus_structure}
          </p>
        )}
      </div>

      {/* equity_offered is a boolean on the backend (apps/backend/app/schemas/jobs.py).
          Renders as a checkbox, not a textarea — the brief's textarea spec
          would 422 on submit. */}
      <div className="flex items-center gap-2 sm:col-span-2">
        <input
          id={equityId}
          type="checkbox"
          className="size-4 cursor-pointer rounded border-input"
          checked={data.equity_offered === true}
          onChange={(e) =>
            onChange("equity_offered", e.target.checked ? true : null)
          }
        />
        <label htmlFor={equityId} className="text-sm text-foreground">
          Equity offered
        </label>
      </div>

      <fieldset className="sm:col-span-2 flex flex-col gap-2">
        <legend className={LABEL_CLASS}>Benefits</legend>
        {benefits.length === 0 && (
          <p className="text-xs text-muted-foreground">
            None yet. Add up to {BENEFITS_MAX_ITEMS}.
          </p>
        )}
        {benefits.map((benefit, index) => (
          <div key={index} className="flex items-center gap-2">
            <Input
              type="text"
              className="min-h-11"
              maxLength={BENEFIT_MAX_LENGTH}
              placeholder="e.g. Medical insurance"
              value={benefit}
              onChange={(e) => updateBenefit(index, e.target.value)}
              aria-label={`Benefit ${index + 1}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="min-h-11 min-w-11"
              onClick={() => removeBenefit(index)}
              aria-label={`Remove benefit ${index + 1}`}
            >
              <X />
            </Button>
          </div>
        ))}
        {errors.benefits && (
          <p className={ERROR_CLASS}>{errors.benefits}</p>
        )}
        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-11"
            onClick={addBenefit}
            disabled={!canAddBenefit}
          >
            <Plus />
            <span>Add benefit</span>
          </Button>
          {!canAddBenefit && (
            <p className="mt-1 text-xs text-muted-foreground">
              Maximum {BENEFITS_MAX_ITEMS} benefits.
            </p>
          )}
        </div>
      </fieldset>
    </div>
  );
}
