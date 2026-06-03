"use client";

import { useEffect, useState } from "react";
import type { AdminStats, AdminTierBreakdown } from "@/lib/api";
import { admin } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import { StatCard, formatNgwee } from "./shared";
import { LlmCostPanel } from "./LlmCostPanel";

export function OverviewTab({
  token,
  stats,
  breakdown,
}: {
  token: string;
  stats: AdminStats | null;
  breakdown: AdminTierBreakdown | null;
}) {
  const [exporting, setExporting] = useState(false);

  const onExportCompanies = async () => {
    setExporting(true);
    try {
      await admin.exportCompaniesCsv(token);
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };
  const statsLoading = !stats;
  const breakdownLoading = !breakdown;
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          className="min-h-9"
          disabled={exporting}
          onClick={() => void onExportCompanies()}
        >
          {exporting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Exporting…
            </>
          ) : (
            "Export Companies CSV"
          )}
        </Button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Users"
          value={stats ? stats.users_total.toLocaleString() : ""}
          hint={stats ? `${stats.users_active_30d} active in 30d` : undefined}
          loading={statsLoading}
        />
        <StatCard
          label="Active subs"
          value={stats ? stats.subscriptions_active.toLocaleString() : ""}
          hint={stats ? `${stats.subscriptions_paid} paying` : undefined}
          loading={statsLoading}
        />
        <StatCard
          label="Jobs active public"
          value={
            stats
              ? (stats.jobs_active_public ?? stats.jobs_active).toLocaleString()
              : ""
          }
          hint={
            stats
              ? `${stats.jobs_active.toLocaleString()} is_active · ${stats.jobs_total.toLocaleString()} total`
              : undefined
          }
          loading={statsLoading}
        />
        <StatCard
          label="Jobs deactivated"
          value={
            stats
              ? (stats.jobs_deactivated ?? stats.jobs_expired).toLocaleString()
              : ""
          }
          loading={statsLoading}
        />
        <StatCard
          label="Need review"
          value={
            stats
              ? (stats.jobs_need_review ?? stats.pending_review_count).toLocaleString()
              : ""
          }
          hint="Missing apply path or deadline"
          loading={statsLoading}
        />
        <StatCard
          label="Matches (24h)"
          value={stats ? stats.matches_24h.toLocaleString() : ""}
          hint={stats ? `${stats.matches_total.toLocaleString()} all time` : undefined}
          loading={statsLoading}
        />
      </div>

      {/* Reserve space for revenue + tier breakdown so the page doesn't
          jump when stats/breakdown resolve. Skeleton inside each card while
          loading; real values once data arrives. */}
      <div className="mt-3 grid sm:grid-cols-2 gap-3">
        <StatCard
          label="Revenue (30d)"
          value={stats ? formatNgwee(stats.revenue_ngwee_30d) : ""}
          loading={statsLoading}
        />
        <StatCard
          label="Revenue (lifetime)"
          value={stats ? formatNgwee(stats.revenue_ngwee_total) : ""}
          loading={statsLoading}
        />
      </div>

      <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Free"
          value={breakdown ? breakdown.free.toLocaleString() : ""}
          hint={
            breakdown
              ? `${Math.round(
                  (breakdown.free / Math.max(breakdown.total_active, 1)) * 100
                )}% of active`
              : undefined
          }
          loading={breakdownLoading}
        />
        <StatCard
          label="Starter"
          value={breakdown ? breakdown.starter.toLocaleString() : ""}
          hint="K125/mo"
          loading={breakdownLoading}
        />
        <StatCard
          label="Professional"
          value={breakdown ? breakdown.professional.toLocaleString() : ""}
          hint="K250/mo"
          loading={breakdownLoading}
        />
        <StatCard
          label="Super Standard"
          value={breakdown ? breakdown.super_standard.toLocaleString() : ""}
          hint="K500/mo · unlimited"
          loading={breakdownLoading}
        />
      </div>

      <LlmCostPanel token={token} />

      <BillingAlertsStrip token={token} />
    </div>
  );
}

function BillingAlertsStrip({ token }: { token: string }) {
  const [health, setHealth] = useState<import("@/lib/api").AdminBillingHealth | null>(null);

  useEffect(() => {
    admin
      .billingHealth(token)
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [token]);

  if (!health) return null;

  const issues: string[] = [];
  if (health.payments_pending > 0) issues.push(`${health.payments_pending} pending payments`);
  if (health.payments_failed_24h > 0) {
    issues.push(`${health.payments_failed_24h} failed payments (24h)`);
  }
  if (!health.lenco_production_ready && health.lenco_environment === "production") {
    issues.push("Lenco production env incomplete");
  }

  if (issues.length === 0) return null;

  return (
    <div
      className="mt-4 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm"
      role="status"
    >
      <p className="font-medium text-destructive">Billing alerts</p>
      <ul className="mt-1 list-disc pl-5 text-muted-foreground">
        {issues.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-muted-foreground">
        Open the <strong>Billing</strong> tab for details, webhook config, and payment drill-down.
      </p>
    </div>
  );
}
