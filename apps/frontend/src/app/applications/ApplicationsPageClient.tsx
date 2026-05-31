"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  savedJobs,
  type ApplicationStatus,
  type SavedJobApplication,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/toast";
import {
  KANBAN_COLUMNS,
  columnForStatus,
  statusForColumnDrop,
  type KanbanColumnId,
} from "@/lib/application-status";
import { KanbanColumn } from "@/components/applications/KanbanColumn";
import { StatusModal } from "@/components/applications/StatusModal";
import { EmptyState } from "@/components/shared/EmptyState";
import { DashboardSkeleton } from "@/components/shared/skeletons/PageSkeletons";

function normalizeApplications(
  rows: SavedJobApplication[] | undefined,
  jobs: SavedJobApplication["job"][],
): SavedJobApplication[] {
  if (rows && rows.length > 0) return rows;
  return jobs.map((job) => ({
    job,
    application_status: "saved",
    status_updated_at: null,
    application_notes: null,
    interview_date: null,
  }));
}

function findColumnFromPoint(clientX: number, clientY: number): KanbanColumnId | null {
  const element = document.elementFromPoint(clientX, clientY);
  if (!element) return null;
  const columnEl = element.closest("[data-kanban-column]") as HTMLElement | null;
  if (!columnEl?.dataset.kanbanColumn) return null;
  return columnEl.dataset.kanbanColumn as KanbanColumnId;
}

export function ApplicationsPageClient() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [applications, setApplications] = useState<SavedJobApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggingJobId, setDraggingJobId] = useState<string | null>(null);
  const [dropHighlight, setDropHighlight] = useState<KanbanColumnId | null>(null);
  const [expandedColumn, setExpandedColumn] = useState<KanbanColumnId>("saved");
  const [selected, setSelected] = useState<SavedJobApplication | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const touchDragRef = useRef<{ jobId: string; active: boolean } | null>(null);

  const loadApplications = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await savedJobs.list(token);
      setApplications(normalizeApplications(res.applications, res.jobs));
    } catch {
      notify.error("Could not load your applications.");
      setApplications([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.replace("/auth?next=/applications");
      return;
    }
    void loadApplications();
  }, [authLoading, isAuthenticated, token, router, loadApplications]);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const sync = () => setIsMobile(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  const grouped = useMemo(() => {
    const map = Object.fromEntries(
      KANBAN_COLUMNS.map((column) => [column.id, [] as SavedJobApplication[]]),
    ) as Record<KanbanColumnId, SavedJobApplication[]>;
    for (const application of applications) {
      const columnId = columnForStatus(application.application_status);
      map[columnId].push(application);
    }
    return map;
  }, [applications]);

  const patchStatus = useCallback(
    async (
      jobId: string,
      payload: {
        status: ApplicationStatus;
        notes?: string | null;
        interview_date?: string | null;
      },
      options?: { rollback?: SavedJobApplication[] },
    ) => {
      if (!token) return;
      const previous = options?.rollback ?? applications;
      setApplications((current) =>
        current.map((item) =>
          item.job.id === jobId
            ? {
                ...item,
                application_status: payload.status,
                application_notes:
                  payload.notes !== undefined ? payload.notes : item.application_notes,
                interview_date:
                  payload.interview_date !== undefined
                    ? payload.interview_date
                    : item.interview_date,
                status_updated_at: new Date().toISOString(),
              }
            : item,
        ),
      );
      try {
        await savedJobs.updateStatus(token, jobId, payload);
      } catch {
        setApplications(previous);
        notify.error("Could not update application status.");
        throw new Error("patch failed");
      }
    },
    [applications, token],
  );

  const handleDrop = useCallback(
    async (columnId: KanbanColumnId, jobId: string) => {
      const current = applications.find((item) => item.job.id === jobId);
      if (!current) return;
      const nextStatus = statusForColumnDrop(columnId, current.application_status);
      if (nextStatus === current.application_status) return;
      const rollback = applications;
      try {
        await patchStatus(
          jobId,
          {
            status: nextStatus,
            notes: current.application_notes,
            interview_date: current.interview_date,
          },
          { rollback },
        );
      } catch {
        /* rollback handled in patchStatus */
      }
    },
    [applications, patchStatus],
  );

  const handleSaveModal = useCallback(
    async (
      jobId: string,
      payload: {
        status: ApplicationStatus;
        notes: string | null;
        interview_date: string | null;
      },
    ) => {
      setSaving(true);
      const rollback = applications;
      try {
        await patchStatus(jobId, payload, { rollback });
        notify.custom.success("Application updated.");
      } finally {
        setSaving(false);
      }
    },
    [applications, patchStatus],
  );

  const onTouchDragStart = useCallback((jobId: string, _target: HTMLElement) => {
    touchDragRef.current = { jobId, active: true };
    setDraggingJobId(jobId);
  }, []);

  useEffect(() => {
    const onTouchMove = (event: TouchEvent) => {
      const drag = touchDragRef.current;
      if (!drag?.active) return;
      event.preventDefault();
      const touch = event.touches[0];
      if (!touch) return;
      const columnId = findColumnFromPoint(touch.clientX, touch.clientY);
      setDropHighlight(columnId);
    };

    const onTouchEnd = (event: TouchEvent) => {
      const drag = touchDragRef.current;
      if (!drag?.active) return;
      const touch = event.changedTouches[0];
      touchDragRef.current = null;
      setDraggingJobId(null);
      if (!touch) {
        setDropHighlight(null);
        return;
      }
      const columnId = findColumnFromPoint(touch.clientX, touch.clientY);
      setDropHighlight(null);
      if (columnId) void handleDrop(columnId, drag.jobId);
    };

    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd);
    window.addEventListener("touchcancel", onTouchEnd);
    return () => {
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("touchcancel", onTouchEnd);
    };
  }, [handleDrop]);

  if (authLoading || loading) {
    return <DashboardSkeleton className="max-w-[1400px]" />;
  }

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-6 pb-10">
      <header className="space-y-2">
        <p className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--muted)" }}>
          Application tracker
        </p>
        <h1 className="font-display text-2xl sm:text-3xl tracking-tight" style={{ color: "var(--ink)" }}>
          Your job applications
        </h1>
        <p className="max-w-2xl text-sm" style={{ color: "var(--muted)" }}>
          Drag saved jobs across stages, add interview dates, and keep notes. Upcoming interviews
          appear in your daily digest.
        </p>
        <Link href="/jobs" className="text-sm font-medium hover:underline" style={{ color: "var(--green-700)" }}>
          Browse jobs to save more
        </Link>
      </header>

      {applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Save roles from the jobs feed, then drag them through your pipeline here."
          ctaText="Browse jobs"
          ctaHref="/jobs"
        />
      ) : isMobile ? (
        <div className="space-y-3">
          {KANBAN_COLUMNS.map((column) => (
            <KanbanColumn
              key={column.id}
              id={column.id}
              label={column.label}
              applications={grouped[column.id]}
              mobileAccordion
              expanded={expandedColumn === column.id}
              onToggle={() =>
                setExpandedColumn((current) => (current === column.id ? "saved" : column.id))
              }
              onDrop={handleDrop}
              onOpenCard={(application) => {
                setSelected(application);
                setModalOpen(true);
              }}
              draggingJobId={draggingJobId}
              onDragStart={setDraggingJobId}
              onDragEnd={() => {
                setDraggingJobId(null);
                setDropHighlight(null);
              }}
              onTouchDragStart={onTouchDragStart}
              dropHighlight={dropHighlight}
              onDragOverColumn={setDropHighlight}
            />
          ))}
        </div>
      ) : (
        <div
          className="flex gap-4 overflow-x-auto overscroll-x-contain scroll-thin pb-4 snap-x snap-mandatory"
          role="region"
          aria-label="Application pipeline board"
          tabIndex={0}
        >
          {KANBAN_COLUMNS.map((column) => (
            <KanbanColumn
              key={column.id}
              id={column.id}
              label={column.label}
              applications={grouped[column.id]}
              onDrop={handleDrop}
              onOpenCard={(application) => {
                setSelected(application);
                setModalOpen(true);
              }}
              draggingJobId={draggingJobId}
              onDragStart={setDraggingJobId}
              onDragEnd={() => {
                setDraggingJobId(null);
                setDropHighlight(null);
              }}
              onTouchDragStart={onTouchDragStart}
              dropHighlight={dropHighlight}
              onDragOverColumn={setDropHighlight}
            />
          ))}
        </div>
      )}

      <StatusModal
        application={selected}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSave={handleSaveModal}
        saving={saving}
      />
    </div>
  );
}
