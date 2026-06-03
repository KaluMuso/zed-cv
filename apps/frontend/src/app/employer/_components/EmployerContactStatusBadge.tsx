import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  pending:
    "bg-amber-500/15 text-amber-800 dark:text-amber-200 border-amber-500/30",
  consented:
    "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200 border-emerald-500/30",
  declined: "bg-red-500/15 text-red-800 dark:text-red-200 border-red-500/30",
  expired: "bg-muted text-muted-foreground border-border",
  draft: "bg-muted text-muted-foreground border-border",
  unavailable: "bg-muted text-muted-foreground border-border",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Awaiting reply",
  consented: "Consented",
  declined: "Declined",
  expired: "Expired",
  draft: "Draft",
  unavailable: "Unavailable",
};

export function EmployerContactStatusBadge({ status }: { status: string }) {
  const key = status.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        STATUS_STYLES[key] ?? STATUS_STYLES.unavailable,
      )}
    >
      {STATUS_LABELS[key] ?? status}
    </span>
  );
}
