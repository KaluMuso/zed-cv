"use client";

import { useEffect, useState } from "react";
import { admin, type AdminMatchRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";
import { formatDate, SkeletonTableRows } from "./shared";

export function MatchesTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminMatchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [minScore, setMinScore] = useState<number | "">("");

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
          <label className="text-xs text-muted-foreground">Min score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => {
              setMinScore(e.target.value === "" ? "" : Number(e.target.value));
              setPage(1);
            }}
            className="h-9 w-24 rounded-md border border-input bg-background px-2 text-sm"
            placeholder="—"
          />
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Job</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <SkeletonTableRows
                  rows={5}
                  widths={["w-28", "w-40", "w-10", "w-16", "w-20"]}
                />
              )}
              {!loading && data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-sm text-muted-foreground">
                    No matches yet.
                  </TableCell>
                </TableRow>
              )}
              {!loading &&
                data.map((m) => (
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
        {pages > 1 && (
          <div className="p-3 flex items-center justify-end gap-2 border-t border-border">
            <Button
              variant="outline"
              size="sm"
              className="min-h-9"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page} of {pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="min-h-9"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
