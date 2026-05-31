"use client";

import { useMemo, useState } from "react";

export type SortDirection = "asc" | "desc";

export function useClientTable<T>(
  rows: T[],
  options: {
    initialSortKey?: keyof T & string;
    getSortValue?: (row: T, key: keyof T & string) => string | number;
  } = {},
) {
  const [sortKey, setSortKey] = useState<(keyof T & string) | null>(
    options.initialSortKey ?? null,
  );
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    const getVal =
      options.getSortValue ??
      ((row: T, key: keyof T & string) => {
        const v = row[key];
        if (typeof v === "number") return v;
        if (typeof v === "string") return v.toLowerCase();
        return String(v ?? "");
      });
    return [...rows].sort((a, b) => {
      const av = getVal(a, sortKey);
      const bv = getVal(b, sortKey);
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [rows, sortKey, sortDir, options.getSortValue]);

  const toggleSort = (key: keyof T & string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortProps = (key: keyof T & string) => ({
    "aria-sort":
      sortKey === key
        ? ((sortDir === "asc" ? "ascending" : "descending") as const)
        : ("none" as const),
    onClick: () => toggleSort(key),
    className: "cursor-pointer select-none hover:text-foreground",
  });

  return {
    sorted,
    sortKey,
    sortDir,
    toggleSort,
    sortProps,
    selected,
    setSelected,
    toggleSelect: (id: string) => {
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    clearSelection: () => setSelected(new Set()),
    selectAll: (ids: string[]) => setSelected(new Set(ids)),
  };
}

export function exportRowsToCsv(filename: string, headers: string[], rows: string[][]) {
  const escape = (cell: string) => {
    if (/[",\n]/.test(cell)) return `"${cell.replace(/"/g, '""')}"`;
    return cell;
  };
  const lines = [headers.map(escape).join(","), ...rows.map((r) => r.map(escape).join(","))];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
