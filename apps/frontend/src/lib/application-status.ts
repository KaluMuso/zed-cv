export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offered"
  | "closed_won"
  | "closed_lost";

export type KanbanColumnId =
  | "saved"
  | "applied"
  | "interviewing"
  | "offered"
  | "closed";

export const KANBAN_COLUMNS: {
  id: KanbanColumnId;
  label: string;
  statuses: ApplicationStatus[];
}[] = [
  { id: "saved", label: "Saved", statuses: ["saved"] },
  { id: "applied", label: "Applied", statuses: ["applied"] },
  { id: "interviewing", label: "Interviewing", statuses: ["interviewing"] },
  { id: "offered", label: "Offered", statuses: ["offered"] },
  { id: "closed", label: "Closed", statuses: ["closed_won", "closed_lost"] },
];

export function columnForStatus(status: ApplicationStatus): KanbanColumnId {
  if (status === "closed_won" || status === "closed_lost") return "closed";
  return status;
}

export function statusForColumnDrop(
  columnId: KanbanColumnId,
  current: ApplicationStatus,
): ApplicationStatus {
  if (columnId === "closed") {
    return current === "closed_lost" ? "closed_lost" : "closed_won";
  }
  return columnId;
}

export const CLOSED_OUTCOME_LABELS: Record<"closed_won" | "closed_lost", string> = {
  closed_won: "Accepted offer",
  closed_lost: "Did not proceed",
};
