"use client";

import type { SavedJobApplication } from "@/lib/api";
import type { KanbanColumnId } from "@/lib/application-status";
import { KanbanCard } from "./KanbanCard";
import { cn } from "@/lib/utils";

export interface KanbanColumnProps {
  id: KanbanColumnId;
  label: string;
  applications: SavedJobApplication[];
  expanded?: boolean;
  onToggle?: () => void;
  mobileAccordion?: boolean;
  onDrop: (columnId: KanbanColumnId, jobId: string) => void;
  onOpenCard: (application: SavedJobApplication) => void;
  draggingJobId: string | null;
  onDragStart: (jobId: string) => void;
  onDragEnd: () => void;
  onTouchDragStart: (jobId: string, target: HTMLElement) => void;
  dropHighlight: KanbanColumnId | null;
  onDragOverColumn: (columnId: KanbanColumnId | null) => void;
}

export function KanbanColumn({
  id,
  label,
  applications,
  expanded = true,
  onToggle,
  mobileAccordion = false,
  onDrop,
  onOpenCard,
  draggingJobId,
  onDragStart,
  onDragEnd,
  onTouchDragStart,
  dropHighlight,
  onDragOverColumn,
}: KanbanColumnProps) {
  const highlighted = dropHighlight === id;
  const dropLabel = `${label} column. Drop applications here.`;

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    onDragOverColumn(id);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const jobId = event.dataTransfer.getData("text/plain");
    if (jobId) onDrop(id, jobId);
    onDragOverColumn(null);
    onDragEnd();
  };

  const body = (
    <div
      data-kanban-column={id}
      role="list"
      aria-label={dropLabel}
      className={cn(
        "kanban-column-body flex min-h-[120px] flex-col gap-2 rounded-xl border p-2 transition-colors",
        highlighted && "ring-2 ring-accent",
      )}
      style={{
        borderColor: highlighted ? "var(--copper-500)" : "var(--line)",
        background: "var(--bg-2)",
      }}
      onDragOver={handleDragOver}
      onDragLeave={() => onDragOverColumn(null)}
      onDrop={handleDrop}
    >
      {applications.length === 0 ? (
        <p className="py-6 text-center text-xs" style={{ color: "var(--muted)" }}>
          Drop jobs here
        </p>
      ) : (
        applications.map((application) => (
          <KanbanCard
            key={application.job.id}
            application={application}
            columnId={id}
            onOpen={onOpenCard}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onTouchDragStart={onTouchDragStart}
            isDragging={draggingJobId === application.job.id}
          />
        ))
      )}
    </div>
  );

  if (mobileAccordion) {
    return (
      <section
        className="kanban-accordion-column rounded-xl border"
        style={{ borderColor: "var(--line)" }}
        aria-labelledby={`kanban-heading-${id}`}
      >
        <button
          type="button"
          id={`kanban-heading-${id}`}
          className="flex min-h-11 w-full items-center justify-between px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 rounded-xl"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-controls={`kanban-panel-${id}`}
        >
          <span className="text-sm font-semibold" style={{ color: "var(--ink)" }}>
            {label}
          </span>
          <span className="flex items-center gap-2 text-xs" style={{ color: "var(--muted)" }}>
            {applications.length}
            <IconChevron expanded={expanded} />
          </span>
        </button>
        {expanded ? (
          <div id={`kanban-panel-${id}`} className="px-2 pb-2">
            {body}
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <section
      className="kanban-column flex min-w-[min(85vw,240px)] flex-1 flex-col gap-2 snap-center"
      aria-labelledby={`kanban-col-${id}`}
    >
      <header className="flex items-center justify-between px-1">
        <h2
          id={`kanban-col-${id}`}
          className="text-xs font-bold uppercase tracking-widest"
          style={{ color: "var(--muted)" }}
        >
          {label}
        </h2>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-mono"
          style={{ background: "var(--bg-2)", color: "var(--muted)" }}
          aria-label={`${applications.length} applications`}
        >
          {applications.length}
        </span>
      </header>
      {body}
    </section>
  );
}

function IconChevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
      style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 200ms" }}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}
