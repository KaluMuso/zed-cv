"use client";

import { useEffect, useState } from "react";
import type { MatchData } from "@/lib/api";
import { ModalPortal } from "@/components/shared/ModalPortal";
import { btnClass } from "@/lib/cn-ui";

export type MatchDismissReason =
  | "not_relevant"
  | "wrong_location"
  | "salary_too_low"
  | "experience_mismatch"
  | "already_applied"
  | "other";

const REASON_OPTIONS: { value: MatchDismissReason; label: string }[] = [
  { value: "not_relevant", label: "Not relevant to my profile" },
  { value: "wrong_location", label: "Wrong location" },
  { value: "salary_too_low", label: "Salary too low" },
  { value: "experience_mismatch", label: "Experience level mismatch" },
  { value: "already_applied", label: "Already applied" },
  { value: "other", label: "Other" },
];

export function MatchDismissModal({
  match,
  open,
  saving,
  onClose,
  onConfirm,
}: {
  match: MatchData | null;
  open: boolean;
  saving?: boolean;
  onClose: () => void;
  onConfirm: (reason: MatchDismissReason | undefined) => void;
}) {
  const [reason, setReason] = useState<MatchDismissReason | "">("");

  useEffect(() => {
    if (open) setReason("");
  }, [open, match?.id]);

  if (!open || !match) return null;

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
        <div className="modal-backdrop" onClick={onClose} aria-hidden />
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="dismiss-match-title"
          className="modal-panel w-full max-w-md rounded-2xl p-5 sm:p-6"
        >
          <h2 id="dismiss-match-title" className="font-display text-lg mb-1">
            Hide this match?
          </h2>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            {match.job.title}
            {match.job.company ? ` · ${match.job.company}` : ""}
          </p>
          <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
            Optional — helps us improve future matches:
          </p>
          <fieldset className="space-y-2 mb-5">
            {REASON_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-2 text-sm cursor-pointer"
              >
                <input
                  type="radio"
                  name="dismiss-reason"
                  value={opt.value}
                  checked={reason === opt.value}
                  onChange={() => setReason(opt.value)}
                  className="h-4 w-4"
                />
                {opt.label}
              </label>
            ))}
          </fieldset>
          <div className="flex gap-2 justify-end">
            <button type="button" className={btnClass("ghost", "sm")} onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button
              type="button"
              className={btnClass("primary", "sm")}
              disabled={saving}
              onClick={() => onConfirm(reason || undefined)}
            >
              {saving ? "Hiding…" : "Hide match"}
            </button>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
