"use client";

import { useEffect, useState } from "react";
import { admin, type AdminMatchRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { formatDate, SkeletonTableRows } from "./shared";
import { useClientTable, sortIsoDate } from "@/components/admin/useClientTable";
import {
  AdminExportButton,
  AdminSortableTableHead,
  AdminTableEmptyRow,
  AdminTablePagination,
} from "@/components/admin/AdminTableTools";

export function MatchesTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminMatchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [minScore, setMinScore] = useState<number | "">("");

  const { sorted, sortProps } = useClientTable(data, {
    getSortValue: (row, key) => {
      if (key === "score") return row.score;
      if (key === "created_at") return sortIsoDate(row.created_at);
      const v = row[key as keyof AdminMatchRow];
      return String(v ?? "").toLowerCase();
    },
  });

  useEffect(() => {
    setLoading(true);
    admin
      .matches(token, {
        page,
        min_score: minScore === "" ? undefined : Number(minScore),
      })
      .then((r) => {
        setData(r.matches);
        setPages(r.pages);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load matches"))
      .finally(() => setLoading(false));
  }, [token, page, minScore]);

  return (
    <Card>
      <CardContent className="p-0">
        <div className="flex flex-wrap gap-2 p-3 border-b border-border items-center">
          <label className="text-xs text-muted-foreground" htmlFor="admin-min-score">
            Min score
          </label>
          <Input
            id="admin-min-score"
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => {
              setMinScore(e.target.value === "" ? "" : Number(e.target.value));
              setPage(1);
            }}
            className="h-9 w-24"
            placeholder="—"
          />
          <AdminExportButton
            filename={`zedapply-matches-p${page}.csv`}
            headers={["user_phone", "job_title", "company", "score", "status", "created"]}
            rows={sorted.map((m) => [
              m.user_phone ?? "",
              m.job_title,
              m.job_company ?? "",
              String(Math.round(m.score)),
              m.status ?? "",
              formatDate(m.created_at),
            ])}
            disabled={loading}
          />
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <AdminSortableTableHead label="User" sortProps={sortProps("user_phone")} />
                <AdminSortableTableHead label="Job" sortProps={sortProps("job_title")} />
                <AdminSortableTableHead label="Score" sortProps={sortProps("score")} />
                <TableHead>Status</TableHead>
                <AdminSortableTableHead label="Created" sortProps={sortProps("created_at")} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <SkeletonTableRows
                  rows={5}
                  widths={["w-28", "w-40", "w-10", "w-16", "w-20"]}
                />
              )}
              {!loading && sorted.length === 0 && (
                <AdminTableEmptyRow
                  colSpan={5}
                  title="No matches yet"
                  description="Matches appear when users run the matching pipeline."
                />
              )}
              {!loading &&
                sorted.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-mono text-xs">{m.user_phone || "—"}</TableCell>
                    <TableCell className="max-w-xs truncate" title={m.job_title}>
                      {m.job_title}
                      {m.job_company && (
                        <span className="text-muted-foreground"> · {m.job_company}</span>
                      )}
                    </TableCell>
                    <TableCell className="tabular-nums font-medium">
                      {Math.round(m.score)}
                    </TableCell>
                    <TableCell>
                      {m.status ? (
                        <Badge variant="secondary">{m.status}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(m.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
        <AdminTablePagination page={page} pages={pages} onPageChange={setPage} />
      </CardContent>
    </Card>
  );
}
