import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TableCell, TableRow } from "@/components/ui/table";

export function formatNgwee(n: number): string {
  return `K${(n / 100).toLocaleString("en-ZM", { maximumFractionDigits: 2 })}`;
}

export function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-ZM");
}

export function StatCard({
  label,
  value,
  hint,
  loading = false,
}: {
  label: string;
  value: string;
  hint?: string;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        {loading ? (
          <CardTitle className="text-2xl tabular-nums">
            <span className="skeleton inline-block h-7 w-24 align-middle" />
          </CardTitle>
        ) : (
          <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
        )}
        {loading ? (
          <span className="skeleton inline-block h-3 w-20 mt-1" />
        ) : (
          hint && <p className="text-xs text-muted-foreground">{hint}</p>
        )}
      </CardHeader>
    </Card>
  );
}

/**
 * N skeleton table rows matching the column layout of the real table.
 * `widths` lets the caller hint per-column width so the placeholder looks
 * like text vs badge vs date instead of N identical bars.
 */
export function SkeletonTableRows({
  rows = 5,
  widths,
}: {
  rows?: number;
  widths: string[];
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRow key={`sk-${i}`}>
          {widths.map((w, j) => (
            <TableCell key={j}>
              <span className={`skeleton inline-block h-4 ${w}`} />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}
