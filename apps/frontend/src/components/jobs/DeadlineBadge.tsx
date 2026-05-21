"use client";

export type DeadlineTone = "green" | "yellow" | "red" | "grey" | "none";

export function deadlineTone(closingDate: string | null | undefined): DeadlineTone {
  if (!closingDate) return "none";
  const end = new Date(closingDate);
  if (Number.isNaN(end.getTime())) return "none";
  const days = Math.ceil((end.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days < 0) return "grey";
  if (days <= 3) return "red";
  if (days <= 14) return "yellow";
  return "green";
}

export function deadlineLabel(closingDate: string | null | undefined): string | null {
  if (!closingDate) return null;
  const end = new Date(closingDate);
  if (Number.isNaN(end.getTime())) return null;
  const days = Math.ceil((end.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days < 0) return "Closed";
  if (days === 0) return "Closes today";
  if (days === 1) return "Closes tomorrow";
  return `Closes in ${days} days`;
}

const TONE_STYLES: Record<Exclude<DeadlineTone, "none">, { bg: string; color: string }> = {
  green: { bg: "var(--green-100)", color: "var(--green-700)" },
  yellow: { bg: "var(--copper-100)", color: "var(--copper-700)" },
  red: { bg: "#fde8e8", color: "var(--danger)" },
  grey: { bg: "var(--bg-2)", color: "var(--muted)" },
};

export function DeadlineBadge({
  closingDate,
  className = "",
}: {
  closingDate: string | null | undefined;
  className?: string;
}) {
  const label = deadlineLabel(closingDate);
  const tone = deadlineTone(closingDate);
  if (!label || tone === "none") return null;
  const style = TONE_STYLES[tone];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
      style={{ background: style.bg, color: style.color }}
    >
      {label}
    </span>
  );
}
