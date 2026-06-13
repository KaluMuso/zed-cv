"use client";

import { Button } from "@/components/ui/button";
import { TableCell, TableHead, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { cn } from "@/lib/utils";
import { exportRowsToCsv } from "./useClientTable";

export function AdminSortableHead({
  label,
  sortProps,
  className,
}: {
  label: string;
  sortProps: {
    onClick: () => void;
    "aria-sort": React.AriaAttributes["aria-sort"];
  };
  className?: string;
}) {
  // aria-sort belongs on <th>, not <button> (jsx-a11y/role-supports-aria-props).
  // Callers wrap this in <TableHead aria-sort={sortProps["aria-sort"]}>.
  return (
    <button
      type="button"
      className={cn(
        "flex w-full cursor-pointer select-none items-center gap-1 text-left font-medium hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 rounded-sm",
        className,
      )}
      onClick={sortProps.onClick}
    >
      {label}
      <span className="text-[10px] text-muted-foreground" aria-hidden>
        {sortProps["aria-sort"] === "ascending"
          ? "↑"
          : sortProps["aria-sort"] === "descending"
            ? "↓"
            : "↕"}
      </span>
    </button>
  );
}

/** Sortable column header — aria-sort on &lt;th&gt;, not the inner button. */
export function AdminSortableTableHead({
  label,
  sortProps,
  className,
}: {
  label: string;
  sortProps: {
    onClick: () => void;
    "aria-sort": React.AriaAttributes["aria-sort"];
  };
  className?: string;
}) {
  return (
    <TableHead aria-sort={sortProps["aria-sort"]} className={className}>
      <AdminSortableHead label={label} sortProps={sortProps} />
    </TableHead>
  );
}

export function AdminTablePagination({
  page,
  pages,
  onPageChange,
}: {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 border-t border-border p-3">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-9"
        disabled={page <= 1}
        onClick={() => onPageChange(1)}
      >
        First
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-9"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className="text-sm text-muted-foreground tabular-nums px-2">
        Page {page} of {pages}
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-9"
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-9"
        disabled={page >= pages}
        onClick={() => onPageChange(pages)}
      >
        Last
      </Button>
    </div>
  );
}

export function AdminExportButton({
  filename,
  headers,
  rows,
  disabled,
  label = "Export CSV",
}: {
  filename: string;
  headers: string[];
  rows: string[][];
  disabled?: boolean;
  label?: string;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="min-h-9"
      disabled={disabled || rows.length === 0}
      onClick={() => exportRowsToCsv(filename, headers, rows)}
    >
      {label}
    </Button>
  );
}

export function AdminTableEmptyRow({
  colSpan,
  title,
  description,
}: {
  colSpan: number;
  title: string;
  description?: string;
}) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan}>
        <EmptyState
          title={title}
          description={description}
          className="border-0 bg-transparent py-10"
        />
      </TableCell>
    </TableRow>
  );
}
