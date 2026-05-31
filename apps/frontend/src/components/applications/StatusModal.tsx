"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ApplicationStatus, SavedJobApplication } from "@/lib/api";
import {
  CLOSED_OUTCOME_LABELS,
  columnForStatus,
} from "@/lib/application-status";

export interface StatusModalProps {
  application: SavedJobApplication | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (
    jobId: string,
    payload: {
      status: ApplicationStatus;
      notes: string | null;
      interview_date: string | null;
    },
  ) => Promise<void>;
  saving?: boolean;
}

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offered", label: "Offered" },
  { value: "closed_won", label: CLOSED_OUTCOME_LABELS.closed_won },
  { value: "closed_lost", label: CLOSED_OUTCOME_LABELS.closed_lost },
];

export function StatusModal({
  application,
  open,
  onOpenChange,
  onSave,
  saving = false,
}: StatusModalProps) {
  const [status, setStatus] = useState<ApplicationStatus>("saved");
  const [notes, setNotes] = useState("");
  const [interviewDate, setInterviewDate] = useState("");

  useEffect(() => {
    if (!application) return;
    setStatus(application.application_status);
    setNotes(application.application_notes ?? "");
    setInterviewDate(application.interview_date ?? "");
  }, [application]);

  const handleSubmit = async () => {
    if (!application) return;
    await onSave(application.job.id, {
      status,
      notes: notes.trim() ? notes.trim() : null,
      interview_date: interviewDate || null,
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" showCloseButton>
        <DialogHeader>
          <DialogTitle>Application details</DialogTitle>
          <DialogDescription>
            {application ? (
              <>
                <span className="font-medium text-foreground">{application.job.title}</span>
                {application.job.company ? ` at ${application.job.company}` : null}
              </>
            ) : (
              "Update notes and interview date"
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <label htmlFor="application-status" className="block space-y-1 text-sm">
            <span className="font-medium" style={{ color: "var(--ink)" }}>
              Status
            </span>
            <select
              id="application-status"
              className="min-h-11 w-full rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: "var(--line)", background: "var(--surface)" }}
              value={status}
              onChange={(event) => setStatus(event.target.value as ApplicationStatus)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              Column: {columnForStatus(status)}
            </span>
          </label>

          <label htmlFor="application-interview-date" className="block space-y-1 text-sm">
            <span className="font-medium" style={{ color: "var(--ink)" }}>
              Interview date
            </span>
            <input
              id="application-interview-date"
              type="date"
              className="min-h-11 w-full rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: "var(--line)", background: "var(--surface)" }}
              value={interviewDate}
              onChange={(event) => setInterviewDate(event.target.value)}
            />
          </label>

          <label htmlFor="application-notes" className="block space-y-1 text-sm">
            <span className="font-medium" style={{ color: "var(--ink)" }}>
              Notes
            </span>
            <textarea
              id="application-notes"
              rows={4}
              className="min-h-[88px] w-full rounded-lg border px-3 py-2 text-sm resize-y"
              style={{ borderColor: "var(--line)", background: "var(--surface)" }}
              placeholder="Recruiter contact, prep reminders, feedback…"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={() => void handleSubmit()} disabled={saving || !application}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
