"use client";

import Link from "next/link";
import type { SavedJobApplication } from "@/lib/api";
import {
  CLOSED_OUTCOME_LABELS,
  columnForStatus,
  type KanbanColumnId,
} from "@/lib/application-status";
import { Icon } from "@/components/ui/Icon";

export interface KanbanCardProps {
  application: SavedJobApplication;
  columnId: KanbanColumnId;
  onOpen: (application: SavedJobApplication) => void;
  onDragStart: (jobId: string) => void;
  onDragEnd: () => void;
  onTouchDragStart: (jobId: string, target: HTMLElement) => void;
  isDragging: boolean;
}

function formatInterviewDate(iso: string | null): string | null {
  if (!iso) return null;
  try {
    return new Date(`${iso}T12:00:00`).toLocaleDateString("en-ZM", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export function KanbanCard({
  application,
  columnId,
  onOpen,
  onDragStart,
  onDragEnd,
  onTouchDragStart,
  isDragging,
}: KanbanCardProps) {
  const { job } = application;
  const interviewLabel = formatInterviewDate(application.interview_date);
  const closedLabel =
    application.application_status === "closed_won" ||
    application.application_status === "closed_lost"
      ? CLOSED_OUTCOME_LABELS[application.application_status]
      : null;

  return (
    <article
      draggable
      data-kanban-card
      data-job-id={job.id}
      data-column-id={columnId}
      onDragStart={(event) => {
        event.dataTransfer.setData("text/plain", job.id);
        event.dataTransfer.effectAllowed = "move";
        onDragStart(job.id);
      }}
      onDragEnd={onDragEnd}
      onTouchStart={(event) => {
        const target = event.currentTarget;
        onTouchDragStart(job.id, target);
      }}
      className={`kanban-card rounded-xl border p-3 cursor-grab active:cursor-grabbing transition-shadow ${
        isDragging ? "opacity-50 ring-2 ring-[var(--copper-500)]" : ""
      }`}
      style={{
        borderColor: "var(--line)",
        background: "var(--surface)",
        touchAction: "none",
      }}
    >
      <button
        type="button"
        className="w-full text-left"
        onClick={() => onOpen(application)}
      >
        <h3 className="text-sm font-semibold leading-snug" style={{ color: "var(--ink)" }}>
          {job.title}
        </h3>
        <p className="mt-1 text-xs truncate" style={{ color: "var(--muted)" }}>
          {job.company || "Company"} · {job.location || "Zambia"}
        </p>
        {interviewLabel ? (
          <p
            className="mt-2 inline-flex items-center gap-1 text-xs font-medium"
            style={{ color: "var(--copper-600)" }}
          >
            <Icon name="calendar" size={12} />
            Interview {interviewLabel}
          </p>
        ) : null}
        {closedLabel ? (
          <p className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
            {closedLabel}
          </p>
        ) : null}
        {application.application_notes ? (
          <p className="mt-2 text-xs line-clamp-2" style={{ color: "var(--ink-2)" }}>
            {application.application_notes}
          </p>
        ) : null}
      </button>
      <div className="mt-2 flex justify-end">
        <Link
          href={`/jobs/${job.id}`}
          className="text-xs font-medium hover:underline"
          style={{ color: "var(--green-700)" }}
          onClick={(event) => event.stopPropagation()}
        >
          View job
        </Link>
      </div>
    </article>
  );
}
