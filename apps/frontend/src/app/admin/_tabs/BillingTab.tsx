"use client";

import { useCallback, useEffect, useState } from "react";
import {
  admin,
  type AdminBillingHealth,
  type AdminPaymentDetail,
  type AdminPaymentRow,
  type AdminStats,
  type AdminSubscriptionRow,
  type AdminTierBreakdown,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { notify } from "@/lib/toast";
import { StatCard, formatNgwee, formatDate, SkeletonTableRows } from "./shared";
import { useClientTable, sortIsoDate } from "@/components/admin/useClientTable";
import {
  AdminExportButton,
  AdminSortableTableHead,
  AdminTableEmptyRow,
  AdminTablePagination,
} from "@/components/admin/AdminTableTools";

function healthTone(ready: boolean): "default" | "destructive" | "secondary" {
  return ready ? "default" : "destructive";
}

function BillingHealthPanel({ health }: { health: AdminBillingHealth | null }) {
  if (!health) {
    return (
      <Card>
        <CardContent className="p-4 text-sm text-muted-foreground">Loading billing health…</CardContent>
      </Card>
    );
  }

  const alerts: string[] = [];
  if (health.payments_pending > 0) {
    alerts.push(`${health.payments_pending} pending payment(s)`);
  }
  if (health.payments_failed_24h > 0) {
    alerts.push(`${health.payments_failed_24h} failed in last 24h`);
  }
  if (!health.lenco_production_ready && health.lenco_environment === "production") {
    alerts.push("Lenco production config incomplete");
  }
  if (health.subscriptions_cancelling > 0) {
    alerts.push(`${health.subscriptions_cancelling} sub(s) cancelling at period end`);
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="p-3 border-b border-border flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">Lenco & billing health</span>
          <Badge variant={healthTone(health.lenco_production_ready)}>
            {health.lenco_environment} ·{" "}
            {health.lenco_production_ready ? "configured" : "check env"}
          </Badge>
          {alerts.map((a) => (
            <Badge key={a} variant="destructive">
              {a}
            </Badge>
          ))}
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-0 divide-y sm:divide-y-0 sm:divide-x divide-border">
          <div className="p-3 text-sm">
            <div className="text-muted-foreground text-xs uppercase tracking-wide">Verify signatures</div>
            <div className="font-medium">{health.lenco_verify_signatures ? "On" : "Off"}</div>
          </div>
          <div className="p-3 text-sm">
            <div className="text-muted-foreground text-xs uppercase tracking-wide">Webhook secret</div>
            <div className="font-medium">{health.lenco_webhook_secret_set ? "Set" : "Missing"}</div>
          </div>
          <div className="p-3 text-sm">
            <div className="text-muted-foreground text-xs uppercase tracking-wide">Completed (24h)</div>
            <div className="font-medium tabular-nums">
              {health.payments_completed_24h} ({health.lenco_completed_24h} Lenco)
            </div>
          </div>
          <div className="p-3 text-sm">
            <div className="text-muted-foreground text-xs uppercase tracking-wide">Webhook URL</div>
            <div className="font-mono text-[10px] break-all">{health.webhook_url_expected}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PaymentDetailModal({
  detail,
  open,
  onClose,
}: {
  detail: AdminPaymentDetail | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{detail?.invoice_number ?? "Payment detail"}</DialogTitle>
        </DialogHeader>
        {!detail ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-muted-foreground">User</div>
                <div>{detail.user_full_name ?? "—"}</div>
                <div className="font-mono text-xs">{detail.user_phone ?? "—"}</div>
                <div className="text-xs">{detail.user_email ?? "—"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Amount</div>
                <div className="font-medium">{formatNgwee(detail.amount)}</div>
                <div className="text-xs capitalize">{detail.status}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Provider / reference</div>
              <div>
                {detail.provider ?? "—"} ·{" "}
                <span className="font-mono text-xs break-all">{detail.provider_ref ?? "—"}</span>
              </div>
            </div>
            {detail.tier_inferred ? (
              <div>
                <div className="text-xs text-muted-foreground">Tier activated</div>
                <div>{detail.tier_inferred}</div>
              </div>
            ) : null}
            {detail.webhook_summary ? (
              <div className="rounded-md border border-border p-2 bg-muted/30">
                <div className="text-xs font-medium mb-1">Webhook payload (summary)</div>
                <pre className="text-[11px] whitespace-pre-wrap break-all">
                  {JSON.stringify(detail.webhook_summary, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No webhook data stored yet.</p>
            )}
            <p className="text-xs text-muted-foreground">
              Created {formatDate(detail.created_at)} · Completed{" "}
              {formatDate(detail.completed_at)}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function BillingTab({
  token,
  stats,
  breakdown,
}: {
  token: string;
  stats: AdminStats | null;
  breakdown: AdminTierBreakdown | null;
}) {
  const [health, setHealth] = useState<AdminBillingHealth | null>(null);
  const [payments, setPayments] = useState<AdminPaymentRow[]>([]);
  const [subs, setSubs] = useState<AdminSubscriptionRow[]>([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingSubs, setLoadingSubs] = useState(true);
  const [payPage, setPayPage] = useState(1);
  const [payPages, setPayPages] = useState(1);
  const [subPage, setSubPage] = useState(1);
  const [subPages, setSubPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [totalCompleted, setTotalCompleted] = useState(0);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [paymentDetail, setPaymentDetail] = useState<AdminPaymentDetail | null>(null);

  const { sorted: sortedSubs, sortProps: subSortProps } = useClientTable(subs, {
    getSortValue: (row, key) => {
      if (key === "matches_used") return row.matches_used;
      if (key === "current_period_end") return sortIsoDate(row.current_period_end);
      const v = row[key as keyof AdminSubscriptionRow];
      return String(v ?? "").toLowerCase();
    },
  });

  const { sorted: sortedPayments, sortProps: paySortProps } = useClientTable(payments, {
    getSortValue: (row, key) => {
      if (key === "amount") return row.amount;
      if (key === "created_at") return sortIsoDate(row.created_at);
      const v = row[key as keyof AdminPaymentRow];
      return String(v ?? "").toLowerCase();
    },
  });

  const loadHealth = useCallback(() => {
    admin
      .billingHealth(token)
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [token]);

  useEffect(() => {
    loadHealth();
    const id = window.setInterval(loadHealth, 60_000);
    return () => window.clearInterval(id);
  }, [loadHealth]);

  useEffect(() => {
    setLoadingPayments(true);
    admin
      .payments(token, {
        page: payPage,
        status: statusFilter || undefined,
        provider: providerFilter || undefined,
      })
      .then((r) => {
        setPayments(r.payments);
        setPayPages(r.pages);
        setTotalCompleted(r.total_completed_ngwee);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load payments"))
      .finally(() => setLoadingPayments(false));
  }, [token, payPage, statusFilter, providerFilter]);

  useEffect(() => {
    setLoadingSubs(true);
    admin
      .subscriptions(token, {
        page: subPage,
        per_page: 15,
        tier: tierFilter || undefined,
      })
      .then((r) => {
        setSubs(r.subscriptions);
        setSubPages(r.pages);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load subscriptions"))
      .finally(() => setLoadingSubs(false));
  }, [token, subPage, tierFilter]);

  const openPayment = async (paymentId: string) => {
    setSelectedPaymentId(paymentId);
    setPaymentDetail(null);
    try {
      const detail = await admin.paymentDetail(token, paymentId);
      setPaymentDetail(detail);
    } catch {
      notify.error("Could not load payment detail");
      setSelectedPaymentId(null);
    }
  };

  return (
    <div className="space-y-4">
      <BillingHealthPanel health={health} />

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
          <div className="p-3 border-b border-border text-sm font-medium">Active subscriptions & usage</div>
          <div className="flex flex-wrap gap-3 p-3 border-b border-border items-center">
            <select
              className="h-9 min-h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={tierFilter}
              onChange={(e) => {
                setTierFilter(e.target.value);
                setSubPage(1);
              }}
            >
              <option value="">All tiers</option>
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="super_standard">Super Standard</option>
            </select>
            <AdminExportButton
              filename={`zedapply-subs-p${subPage}.csv`}
              headers={["phone", "tier", "usage", "period_end", "status"]}
              rows={sortedSubs.map((s) => [
                s.user_phone ?? "",
                s.tier,
                `${s.matches_used}/${s.matches_limit >= 99999 ? "unlimited" : s.matches_limit}`,
                formatDate(s.current_period_end),
                s.cancelled_at ? "cancelling" : s.status,
              ])}
              disabled={loadingSubs}
            />
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <AdminSortableTableHead label="Phone" sortProps={subSortProps("user_phone")} />
                  <AdminSortableTableHead label="Tier" sortProps={subSortProps("tier")} />
                  <AdminSortableTableHead label="Usage" sortProps={subSortProps("matches_used")} />
                  <AdminSortableTableHead label="Period end" sortProps={subSortProps("current_period_end")} />
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingSubs && (
                  <SkeletonTableRows rows={4} widths={["w-28", "w-16", "w-20", "w-20", "w-16"]} />
                )}
                {!loadingSubs && sortedSubs.length === 0 && (
                  <AdminTableEmptyRow colSpan={5} title="No subscriptions" />
                )}
                {!loadingSubs &&
                  sortedSubs.map((s) => (
                    <TableRow key={s.user_id}>
                      <TableCell className="font-mono text-xs">{s.user_phone ?? "—"}</TableCell>
                      <TableCell>{s.tier.replace("_", " ")}</TableCell>
                      <TableCell className="tabular-nums text-xs">
                        {s.matches_used} / {s.matches_limit >= 99999 ? "∞" : s.matches_limit}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(s.current_period_end)}
                      </TableCell>
                      <TableCell>
                        {s.cancelled_at ? (
                          <Badge variant="secondary">Cancelling</Badge>
                        ) : (
                          <Badge variant={s.status === "active" ? "default" : "destructive"}>
                            {s.status}
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
          <AdminTablePagination page={subPage} pages={subPages} onPageChange={setSubPage} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="p-3 border-b border-border text-sm font-medium">Payments & invoices</div>
          <div className="flex flex-wrap gap-3 p-3 border-b border-border items-center">
            <select
              className="h-9 min-h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPayPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
            <select
              className="h-9 min-h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={providerFilter}
              onChange={(e) => {
                setProviderFilter(e.target.value);
                setPayPage(1);
              }}
            >
              <option value="">All providers</option>
              <option value="lenco">Lenco</option>
              <option value="dpo_pay">DPO Pay</option>
            </select>
            <p className="ml-auto text-sm text-muted-foreground">
              Lifetime completed:{" "}
              <span className="font-medium text-foreground">{formatNgwee(totalCompleted)}</span>
            </p>
            <AdminExportButton
              filename={`zedapply-payments-p${payPage}.csv`}
              headers={["invoice", "phone", "amount_ngwee", "provider", "status", "created"]}
              rows={sortedPayments.map((p) => [
                p.invoice_number ?? "",
                p.user_phone ?? "",
                String(p.amount),
                p.provider ?? "",
                p.status,
                formatDate(p.created_at),
              ])}
              disabled={loadingPayments}
            />
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <AdminSortableTableHead label="Invoice" sortProps={paySortProps("invoice_number")} />
                  <AdminSortableTableHead label="Phone" sortProps={paySortProps("user_phone")} />
                  <AdminSortableTableHead label="Amount" sortProps={paySortProps("amount")} />
                  <AdminSortableTableHead label="Provider" sortProps={paySortProps("provider")} />
                  <AdminSortableTableHead label="Status" sortProps={paySortProps("status")} />
                  <AdminSortableTableHead label="Created" sortProps={paySortProps("created_at")} />
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingPayments && (
                  <SkeletonTableRows rows={5} widths={["w-20", "w-28", "w-16", "w-12", "w-16", "w-20", "w-12"]} />
                )}
                {!loadingPayments && sortedPayments.length === 0 && (
                  <AdminTableEmptyRow colSpan={7} title="No payments yet" />
                )}
                {!loadingPayments &&
                  sortedPayments.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">{p.invoice_number ?? "—"}</TableCell>
                      <TableCell className="font-mono text-xs">{p.user_phone ?? "—"}</TableCell>
                      <TableCell className="tabular-nums">{formatNgwee(p.amount)}</TableCell>
                      <TableCell className="text-xs">{p.provider ?? "—"}</TableCell>
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
                      <TableCell>
                        <Button type="button" variant="outline" size="sm" onClick={() => void openPayment(p.id)}>
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
          <AdminTablePagination page={payPage} pages={payPages} onPageChange={setPayPage} />
        </CardContent>
      </Card>

      <PaymentDetailModal
        detail={paymentDetail}
        open={Boolean(selectedPaymentId)}
        onClose={() => {
          setSelectedPaymentId(null);
          setPaymentDetail(null);
        }}
      />
    </div>
  );
}
