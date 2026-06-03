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

export type MatchDismissPayload = {
  reason?: MatchDismissReason;
  note?: string;
};

const REASON_OPTIONS: { value: MatchDismissReason; label: string }[] = [
  { value: "not_relevant", label: "Not relevant to my profile" },
  { value: "wrong_location", label: "Wrong location" },
  { value: "salary_too_low", label: "Salary too low" },
  { value: "experience_mismatch", label: "Experience level mismatch" },
  { value: "already_applied", label: "Already applied" },
  { value: "other", label: "Other" },
];

const NOTE_MAX = 500;

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
  onConfirm: (payload: MatchDismissPayload) => void;
}) {
  const [reason, setReason] = useState<MatchDismissReason | "">("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (open) {
      setReason("");
      setNote("");
    }
  }, [open, match?.id]);

  if (!open || !match) return null;

  const trimmedNote = note.trim();
  const noteInvalid = reason === "other" && trimmedNote.length === 0;

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
          <fieldset className="space-y-2 mb-3">
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
          {reason === "other" && (
            <label className="flex flex-col gap-1.5 mb-4">
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                Tell us more <span style={{ color: "var(--danger)" }}>*</span>
              </span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={NOTE_MAX}
                rows={3}
                placeholder="e.g. role is too senior, industry mismatch…"
                className="form-input text-sm"
                style={{
                  resize: "vertical",
                  padding: 10,
                  border: noteInvalid
                    ? "1px solid var(--danger)"
                    : "1px solid var(--line-2)",
                }}
                aria-invalid={noteInvalid}
              />
              {noteInvalid && (
                <span className="text-xs" style={{ color: "var(--danger)" }}>
                  Please add a short note when you choose Other.
                </span>
              )}
            </label>
          )}
          <div className="flex gap-2 justify-end">
            <button type="button" className={btnClass("ghost", "sm")} onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button
              type="button"
              className={btnClass("primary", "sm")}
              disabled={saving || noteInvalid}
              onClick={() => {
                const payload: MatchDismissPayload = {};
                if (reason) payload.reason = reason;
                if (reason === "other" && trimmedNote) payload.note = trimmedNote;
                onConfirm(payload);
              }}
            >
              {saving ? "Hiding…" : "Hide match"}
            </button>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
