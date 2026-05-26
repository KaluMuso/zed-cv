"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  profile as profileApi,
  subscription as subscriptionApi,
  type PaymentHistoryRow,
  type Subscription,
  type UserProfile,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { formatMatchesLimit } from "@/lib/tier-config";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";

function formatWelcomeEnd(iso: string | null | undefined): string {
  if (!iso) return "soon";
  try {
    return new Date(iso).toLocaleDateString("en-ZM", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "soon";
  }
}

function formatNgwee(amount: number, currency: string): string {
  const major = amount / 100;
  const symbol = currency === "USD" ? "$" : "K";
  return `${symbol}${major.toLocaleString("en-ZM", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

function formatPaymentMethod(method: string): string {
  const labels: Record<string, string> = {
    mtn_money: "MTN Mobile Money",
    airtel_money: "Airtel Money",
    mtn: "MTN Mobile Money",
    airtel: "Airtel Money",
    card: "Card",
    lenco: "Lenco",
    lenco_mtn_money: "Lenco · MTN",
    lenco_airtel_money: "Lenco · Airtel",
    lenco_card: "Lenco · Card",
  };
  return labels[method] ?? method.replace(/_/g, " ");
}

function formatPaymentDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-ZM", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function statusLabel(status: string): string {
  if (status === "completed") return "Paid";
  if (status === "pending") return "Pending";
  if (status === "failed") return "Failed";
  if (status === "refunded") return "Refunded";
  return status;
}

function PaymentRow({ row }: { row: PaymentHistoryRow }) {
  const date = formatPaymentDate(row.completed_at ?? row.created_at);
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 py-3 border-b border-[var(--line)] last:border-0"
    >
      <div>
        <div className="text-sm font-medium">{formatNgwee(row.amount, row.currency)}</div>
        <div className="text-xs" style={{ color: "var(--muted)" }}>
          {formatPaymentMethod(row.payment_method)}
          {row.provider ? ` · ${row.provider}` : ""}
          {" · "}
          {date}
        </div>
      </div>
      <span
        className="text-xs font-medium uppercase tracking-wide self-start sm:self-center"
        style={{
          color:
            row.status === "completed"
              ? "var(--green-700)"
              : row.status === "failed"
                ? "var(--destructive, #b91c1c)"
                : "var(--muted)",
        }}
      >
        {statusLabel(row.status)}
      </span>
    </div>
  );
}

export function BillingSection() {
  const { token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [payments, setPayments] = useState<PaymentHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      profileApi.get(token),
      subscriptionApi.get(token).catch(() => null),
      subscriptionApi.listPayments(token).catch(() => ({ payments: [], total: 0 })),
    ])
      .then(([p, s, pay]) => {
        setProfile(p);
        setSub(s);
        setPayments(pay.payments);
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading billing…</p>;
  }

  if (!profile) {
    return <p className="text-sm text-muted-foreground">Could not load plan.</p>;
  }

  const tier = profile.subscription_tier;
  const tierLabel = TIER_NAV_LABELS[tier] ?? tier;
  const limitLabel = sub ? formatMatchesLimit(sub.matches_limit) : "—";
  const usageLine =
    sub && sub.matches_limit < 99999
      ? `${sub.matches_used} of ${limitLabel} matches used this period`
      : sub
        ? `${sub.matches_used} matches used (unlimited plan)`
        : null;

  const lastCompleted = payments.find((p) => p.status === "completed");

  return (
    <div>
      <SettingsSectionHeader title="Billing" />

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Current plan</div>
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="font-display text-3xl mb-1" style={{ letterSpacing: "-0.02em" }}>
              {tierLabel}
            </div>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {tier === "free"
                ? sub?.welcome_bonus_active
                  ? `${sub.matches_limit} matches/mo (welcome bonus) until ${formatWelcomeEnd(sub.welcome_match_bonus_until)}`
                  : "Free tier with monthly match allowance"
                : usageLine}
            </p>
          </div>
          {tier !== "super_standard" ? (
            <Link href="/pricing" className="btn btn-primary btn-sm shrink-0">
              Upgrade plan
              <Icon name="arrowRight" size={14} />
            </Link>
          ) : (
            <Link href="/pricing" className="btn btn-outline btn-sm shrink-0">
              View plans
            </Link>
          )}
        </div>
      </SettingsCard>

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Payment method</div>
        {lastCompleted ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Last payment via {formatPaymentMethod(lastCompleted.payment_method)} on{" "}
            {formatPaymentDate(lastCompleted.completed_at ?? lastCompleted.created_at)}. New
            payments are added at checkout on the{" "}
            <Link href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              pricing page
            </Link>
            .
          </p>
        ) : (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No payment method on file. Add one when you upgrade on the{" "}
            <Link href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              pricing page
            </Link>{" "}
            (DPO Pay or Lenco mobile money).
          </p>
        )}
      </SettingsCard>

      <SettingsCard>
        <div className="eyebrow mb-2">Invoices</div>
        {payments.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No invoices yet. Completed payments will appear here after you upgrade.
          </p>
        ) : (
          <div>{payments.map((p) => <PaymentRow key={p.id} row={p} />)}</div>
        )}
      </SettingsCard>
    </div>
  );
}
