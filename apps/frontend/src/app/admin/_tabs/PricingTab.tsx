"use client";

import { useEffect, useState } from "react";
import {
  admin,
  type AdminPaymentRow,
  type AdminStats,
  type AdminTierBreakdown,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { notify } from "@/lib/toast";
import { StatCard, formatNgwee, formatDate, SkeletonTableRows } from "./shared";

export function PricingTab({
  token,
  stats,
  breakdown,
}: {
  token: string;
  stats: AdminStats | null;
  breakdown: AdminTierBreakdown | null;
}) {
  const [data, setData] = useState<AdminPaymentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [totalCompleted, setTotalCompleted] = useState(0);

  useEffect(() => {
    setLoading(true);
    admin
      .payments(token, { page, status: statusFilter || undefined })
      .then((r) => {
        setData(r.payments);
        setPages(r.pages);
        setTotalCompleted(r.total_completed_ngwee);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load payments"))
      .finally(() => setLoading(false));
  }, [token, page, statusFilter]);

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        <StatCard
          label="Revenue (30d)"
          value={stats ? formatNgwee(stats.revenue_ngwee_30d) : "—"}
        />
        <StatCard
          label="Revenue (lifetime)"
          value={stats ? formatNgwee(stats.revenue_ngwee_total) : "—"}
        />
      </div>

      {breakdown && (
        <Card>
          <CardContent className="p-0">
            <div className="p-3 border-b border-border text-sm font-medium">
              Tier breakdown · {breakdown.total_active.toLocaleString()} active
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tier</TableHead>
                  <TableHead>Active subs</TableHead>
                  <TableHead>Share</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(["free", "starter", "professional", "super_standard"] as const).map((t) => {
                  const count = breakdown[t];
                  const pct = breakdown.total_active
                    ? Math.round((count / breakdown.total_active) * 100)
                    : 0;
                  return (
                    <TableRow key={t}>
                      <TableCell>{t.replace("_", " ")}</TableCell>
                      <TableCell className="tabular-nums">{count.toLocaleString()}</TableCell>
                      <TableCell className="tabular-nums">{pct}%</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap gap-3 p-3 border-b border-border items-center">
            <select
              className="h-9 min-h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
            <p className="ml-auto text-sm text-muted-foreground">
              Lifetime completed:{" "}
              <span className="font-medium text-foreground">{formatNgwee(totalCompleted)}</span>
            </p>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phone</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && (
                  <SkeletonTableRows
                    rows={5}
                    widths={["w-28", "w-16", "w-16", "w-16", "w-20"]}
                  />
                )}
                {!loading && data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-sm text-muted-foreground">No payments yet.</TableCell>
                  </TableRow>
                )}
                {!loading &&
                  data.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">{p.user_phone || "—"}</TableCell>
                      <TableCell className="tabular-nums">{formatNgwee(p.amount)}</TableCell>
                      <TableCell className="text-xs">{p.payment_method}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            p.status === "completed"
                              ? "default"
                              : p.status === "failed" || p.status === "refunded"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {p.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDate(p.created_at)}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
          {pages > 1 && (
            <div className="p-3 flex items-center justify-end gap-2 border-t border-border">
              <Button variant="outline" size="sm" className="min-h-9" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
              <span className="text-sm text-muted-foreground">Page {page} of {pages}</span>
              <Button variant="outline" size="sm" className="min-h-9" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
