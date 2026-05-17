"use client";

import { useEffect } from "react";
import { z } from "zod";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import type { AdminJobCreatePayload } from "../types";
import {
  EMPLOYMENT_TYPES,
  HYBRID_DAYS_MAX,
  HYBRID_DAYS_MIN,
  WORK_ARRANGEMENTS,
} from "../job-enums";

// Schema bounds mirror backend Pydantic (AdminJobCreate). title cap 5000
// matches min_length=1, max_length=5000. company cap 500. location is
// unbounded server-side — we keep it loose here.
export const step1Schema = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, "Title is required")
      .max(5000, "Title is too long"),
    company: z
      .string()
      .trim()
      .min(1, "Company is required")
      .max(500, "Company name is too long"),
    location: z
      .string()
      .trim()
      .min(1, "Location is required"),
    employment_type: z.enum([
      "full_time",
      "part_time",
      "contract",
      "freelance",
      "internship",
      "temporary",
    ]),
    work_arrangement: z.enum(["remote", "hybrid", "on_site"]),
    hybrid_days_per_week: z
      .number()
      .int()
      .min(HYBRID_DAYS_MIN)
      .max(HYBRID_DAYS_MAX)
      .nullable()
      .optional(),
  })
  .superRefine((val, ctx) => {
    if (val.work_arrangement === "hybrid") {
      if (
        val.hybrid_days_per_week == null ||
        val.hybrid_days_per_week < HYBRID_DAYS_MIN ||
        val.hybrid_days_per_week > HYBRID_DAYS_MAX
      ) {
        ctx.addIssue({
          code: "custom",
          path: ["hybrid_days_per_week"],
          message: `Pick ${HYBRID_DAYS_MIN}–${HYBRID_DAYS_MAX} days when hybrid`,
        });
      }
    }
  });

export type Step1Data = z.infer<typeof step1Schema>;

type FieldErrors = Partial<Record<keyof Step1Data, string | undefined>>;

export type StepBasicInfoProps = {
  data: Partial<AdminJobCreatePayload>;
  errors: FieldErrors;
  onChange: <K extends keyof AdminJobCreatePayload>(
    field: K,
    value: AdminJobCreatePayload[K] | undefined,
  ) => void;
};

// Native <select> styled like the rest of the admin UI (matches
// _tabs/JobsTab.tsx). The shared ui/ kit doesn't ship a Select primitive
// yet — when it does, swap this out.
const SELECT_CLASS =
  "h-11 min-h-11 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50";

const LABEL_CLASS =
  "text-sm font-medium leading-none text-foreground";

const REQUIRED_MARK = (
  <span aria-hidden="true" className="ml-0.5 text-destructive">
    *
  </span>
);

const ERROR_CLASS = "text-xs text-destructive";

export function StepBasicInfo({ data, errors, onChange }: StepBasicInfoProps) {
  const titleId = "step1-title";

  // Autofocus title on first mount only. The Input wrapper in
  // components/ui/input.tsx doesn't forward refs, so we hop through the
  // DOM by id. Cheap and avoids touching the shared primitive.
  useEffect(() => {
    const el = document.getElementById(titleId);
    if (el instanceof HTMLInputElement) {
      el.focus();
    }
  }, []);
  const companyId = "step1-company";
  const locationId = "step1-location";
  const employmentId = "step1-employment-type";
  const arrangementId = "step1-work-arrangement";
  const hybridId = "step1-hybrid-days";

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <label htmlFor={titleId} className={LABEL_CLASS}>
          Title{REQUIRED_MARK}
        </label>
        <Input
          id={titleId}
          type="text"
          required
          className="min-h-11"
          value={data.title ?? ""}
          onChange={(e) => onChange("title", e.target.value)}
          aria-invalid={errors.title ? "true" : undefined}
          aria-describedby={errors.title ? `${titleId}-error` : undefined}
          maxLength={5000}
        />
        {errors.title && (
          <p id={`${titleId}-error`} className={ERROR_CLASS}>
            {errors.title}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={companyId} className={LABEL_CLASS}>
          Company{REQUIRED_MARK}
        </label>
        <Input
          id={companyId}
          type="text"
          required
          className="min-h-11"
          value={data.company ?? ""}
          onChange={(e) => onChange("company", e.target.value)}
          aria-invalid={errors.company ? "true" : undefined}
          aria-describedby={errors.company ? `${companyId}-error` : undefined}
          maxLength={500}
        />
        {errors.company && (
          <p id={`${companyId}-error`} className={ERROR_CLASS}>
            {errors.company}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={locationId} className={LABEL_CLASS}>
          Location{REQUIRED_MARK}
        </label>
        <Input
          id={locationId}
          type="text"
          required
          className="min-h-11"
          placeholder="e.g. Lusaka"
          value={data.location ?? ""}
          onChange={(e) => onChange("location", e.target.value)}
          aria-invalid={errors.location ? "true" : undefined}
          aria-describedby={errors.location ? `${locationId}-error` : undefined}
        />
        {errors.location && (
          <p id={`${locationId}-error`} className={ERROR_CLASS}>
            {errors.location}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={employmentId} className={LABEL_CLASS}>
          Employment type{REQUIRED_MARK}
        </label>
        <select
          id={employmentId}
          required
          className={SELECT_CLASS}
          value={data.employment_type ?? ""}
          onChange={(e) =>
            onChange(
              "employment_type",
              e.target.value
                ? (e.target.value as AdminJobCreatePayload["employment_type"])
                : undefined,
            )
          }
          aria-invalid={errors.employment_type ? "true" : undefined}
          aria-describedby={
            errors.employment_type ? `${employmentId}-error` : undefined
          }
        >
          <option value="" disabled>
            Select an employment type…
          </option>
          {EMPLOYMENT_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.employment_type && (
          <p id={`${employmentId}-error`} className={ERROR_CLASS}>
            {errors.employment_type}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={arrangementId} className={LABEL_CLASS}>
          Work arrangement{REQUIRED_MARK}
        </label>
        <select
          id={arrangementId}
          required
          className={SELECT_CLASS}
          value={data.work_arrangement ?? ""}
          onChange={(e) => {
            const next = e.target.value
              ? (e.target.value as AdminJobCreatePayload["work_arrangement"])
              : undefined;
            onChange("work_arrangement", next);
            // Clear hybrid_days when switching away so we don't ship a
            // stale value to the backend.
            if (next !== "hybrid") {
              onChange("hybrid_days_per_week", null);
            }
          }}
          aria-invalid={errors.work_arrangement ? "true" : undefined}
          aria-describedby={
            errors.work_arrangement ? `${arrangementId}-error` : undefined
          }
        >
          <option value="" disabled>
            Select a work arrangement…
          </option>
          {WORK_ARRANGEMENTS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.work_arrangement && (
          <p id={`${arrangementId}-error`} className={ERROR_CLASS}>
            {errors.work_arrangement}
          </p>
        )}
      </div>

      {data.work_arrangement === "hybrid" && (
        <div className={cn("flex flex-col gap-1.5 sm:col-span-2")}>
          <label htmlFor={hybridId} className={LABEL_CLASS}>
            Hybrid days per week{REQUIRED_MARK}
          </label>
          <Input
            id={hybridId}
            type="number"
            min={HYBRID_DAYS_MIN}
            max={HYBRID_DAYS_MAX}
            required
            className="min-h-11 sm:w-48"
            value={data.hybrid_days_per_week ?? ""}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") {
                onChange("hybrid_days_per_week", null);
                return;
              }
              const n = Number(raw);
              onChange(
                "hybrid_days_per_week",
                Number.isFinite(n) ? n : null,
              );
            }}
            aria-invalid={errors.hybrid_days_per_week ? "true" : undefined}
            aria-describedby={
              errors.hybrid_days_per_week
                ? `${hybridId}-error`
                : `${hybridId}-help`
            }
          />
          <p id={`${hybridId}-help`} className="text-xs text-muted-foreground">
            Between {HYBRID_DAYS_MIN} and {HYBRID_DAYS_MAX}.
          </p>
          {errors.hybrid_days_per_week && (
            <p id={`${hybridId}-error`} className={ERROR_CLASS}>
              {errors.hybrid_days_per_week}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
