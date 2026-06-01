"use client";

import { useEffect, useMemo, useState } from "react";
import {
  admin,
  type AdminPaymentRow,
  type AdminSubscriptionMetrics,
  type AdminTierBreakdown,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { notify } from "@/lib/toast";
import { StatCard, formatNgwee, formatDate, SkeletonTableRows } from "./shared";
import { useClientTable, sortIsoDate } from "@/components/admin/useClientTable";
import {
  AdminExportButton,
  AdminSortableTableHead,
  AdminTableEmptyRow,
  AdminTablePagination,
} from "@/components/admin/AdminTableTools";

const PAYMENTS_PER_PAGE = 25;

export function SubscriptionsTab({ token }: { token: string }) {
  const [metrics, setMetrics] = useState<AdminSubscriptionMetrics | null>(null);
  const [breakdown, setBreakdown] = useState<AdminTierBreakdown | null>(null);
  const [payments, setPayments] = useState<AdminPaymentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [payPage, setPayPage] = useState(1);

  const { sorted, sortProps } = useClientTable(payments, {
    getSortValue: (row, key) => {
      if (key === "amount") return row.amount;
      if (key === "created_at") return sortIsoDate(row.completed_at ?? row.created_at);
      const v = row[key as keyof AdminPaymentRow];
      return String(v ?? "").toLowerCase();
    },
  });

  const payPages = Math.max(1, Math.ceil(sorted.length / PAYMENTS_PER_PAGE));
  const pagedPayments = useMemo(() => {
    const start = (payPage - 1) * PAYMENTS_PER_PAGE;
    return sorted.slice(start, start + PAYMENTS_PER_PAGE);
  }, [sorted, payPage]);

  useEffect(() => {
    if (payPage > payPages) setPayPage(payPages);
  }, [payPage, payPages]);

  useEffect(() => {
    setPayPage(1);
  }, [payments.length]);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      admin.subscriptionMetrics(token),
      admin.subscriptions(token, { per_page: 1 }),
      admin.payments(token, { page: 1, per_page: 50 }),
    ])
      .then(([m, subs, pay]) => {
        setMetrics(m);
        setBreakdown(subs.breakdown);
        setPayments(pay.payments);
      })
      .catch((e) =>
        notify.error(e instanceof Error ? e.message : "Failed to load subscriptions"),
      )
      .finally(() => setLoading(false));
  }, [token]);

  const churnPct =
    metrics && metrics.active_at_month_start > 0
      ? `${Math.round(metrics.churn_rate * 100)}%`
      : "—";

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        <StatCard
          label="MRR (monthly)"
          value={
            metrics
              ? `K${metrics.mrr_kwacha.toLocaleString(undefined, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 2,
                })}`
              : loading
                ? ""
                : "—"
          }
          hint={
            metrics
              ? `${metrics.active_subscriptions} active subs · ${metrics.mrr_ngwee.toLocaleString()} ngwee`
              : undefined
          }
        />
        <StatCard
          label="Churn (this month)"
          value={metrics ? churnPct : loading ? "" : "—"}
          hint={
            metrics
              ? `${metrics.cancelled_this_month} cancelled / ${metrics.active_at_month_start} active at month start`
              : undefined
          }
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
          <div className="flex flex-wrap items-center gap-2 p-3 border-b border-border">
            <span className="text-sm font-medium">Recent payments (last 50)</span>
            <div className="ml-auto">
            <AdminExportButton
              filename="zedapply-recent-payments.csv"
              headers={["when", "phone", "amount", "method", "status"]}
              rows={sorted.map((p) => [
                formatDate(p.completed_at ?? p.created_at),
                p.user_phone ?? "",
                formatNgwee(p.amount),
                p.payment_method ?? "",
                p.status,
              ])}
              disabled={loading}
            />
            </div>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <AdminSortableTableHead label="When" sortProps={sortProps("created_at")} />
                  <AdminSortableTableHead label="Phone" sortProps={sortProps("user_phone")} />
                  <AdminSortableTableHead label="Amount" sortProps={sortProps("amount")} />
                  <AdminSortableTableHead label="Method" sortProps={sortProps("payment_method")} />
                  <AdminSortableTableHead label="Status" sortProps={sortProps("status")} />
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <SkeletonTableRows rows={5} widths={["w-24", "w-28", "w-20", "w-20", "w-16"]} />
                ) : sorted.length === 0 ? (
                  <AdminTableEmptyRow colSpan={5} title="No payments yet" />
                ) : (
                  pagedPayments.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="text-xs whitespace-nowrap">
                        {formatDate(p.completed_at ?? p.created_at)}
                      </TableCell>
                      <TableCell className="text-xs">{p.user_phone ?? "—"}</TableCell>
                      <TableCell className="tabular-nums">{formatNgwee(p.amount)}</TableCell>
                      <TableCell className="text-xs">{p.payment_method}</TableCell>
                      <TableCell className="text-xs">{p.status}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          <AdminTablePagination page={payPage} pages={payPages} onPageChange={setPayPage} />
        </CardContent>
      </Card>
    </div>
  );
}
