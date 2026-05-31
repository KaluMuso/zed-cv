"use client";

import Link from "next/link";
import type { SavedJobApplication } from "@/lib/api";
import {
  CLOSED_OUTCOME_LABELS,
  type KanbanColumnId,
} from "@/lib/application-status";
import { Icon } from "@/components/ui/Icon";
import { isJobListingClosed } from "@/lib/isJobListingClosed";
import { surfaceCardClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

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
  const jobClosed = isJobListingClosed(job);
  const dragLabel = `Move ${job.title} to another stage`;

  const startDrag = (event: React.DragEvent<HTMLButtonElement>) => {
    event.dataTransfer.setData("text/plain", job.id);
    event.dataTransfer.effectAllowed = "move";
    onDragStart(job.id);
  };

  return (
    <article
      data-kanban-card
      data-job-id={job.id}
      data-column-id={columnId}
      className={cn(
        surfaceCardClass,
        "kanban-card p-3 transition-shadow",
        isDragging && "opacity-50 ring-2 ring-accent",
      )}
      aria-grabbed={isDragging}
    >
      <div className="flex gap-2">
        <button
          type="button"
          draggable
          className="kanban-drag-handle flex size-11 min-h-11 min-w-11 shrink-0 cursor-grab items-center justify-center rounded-md border border-border bg-muted/40 text-muted-foreground active:cursor-grabbing focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30"
          aria-label={dragLabel}
          onDragStart={startDrag}
          onDragEnd={onDragEnd}
          onTouchStart={(event) => {
            onTouchDragStart(job.id, event.currentTarget);
          }}
        >
          <Icon name="gripVertical" size={16} aria-hidden />
        </button>
        <button
          type="button"
          className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 rounded-md"
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
              <Icon name="calendar" size={12} aria-hidden />
              Interview {interviewLabel}
            </p>
          ) : null}
          {jobClosed ? (
            <span
              className="mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
              style={{ background: "var(--muted)", color: "#faf7f2" }}
            >
              Job closed
            </span>
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
      </div>
      <div className="mt-2 flex justify-end">
        <Link
          href={`/jobs/${job.id}`}
          className="min-h-11 inline-flex items-center px-2 text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 rounded-sm"
          style={{ color: "var(--green-700)" }}
          onClick={(event) => event.stopPropagation()}
        >
          View job
        </Link>
      </div>
    </article>
  );
}
