"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  profile as profileApi,
  subscription as subscriptionApi,
  type PaymentHistoryRow,
  type Subscription,
  type UserProfile,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/toast";
import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import { formatMatchesLimit } from "@/lib/tier-config";
import { TIER_NAV_LABELS } from "@/lib/tier-display";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";
import { InvoicePanel } from "../_components/InvoicePanel";

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

export function BillingSection() {
  const { token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [payments, setPayments] = useState<PaymentHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const reload = useCallback(() => {
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

  useEffect(() => {
    reload();
  }, [reload]);

  const handleCancel = async () => {
    if (!token || !window.confirm(
      "Cancel your paid plan at the end of this billing period? You keep access until then, then revert to Free.",
    )) {
      return;
    }
    setCancelling(true);
    try {
      const res = await subscriptionApi.cancel(token);
      notify.success(res.message);
      reload();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not cancel plan");
    } finally {
      setCancelling(false);
    }
  };

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
            {sub?.expires_at && tier !== "free" ? (
              <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
                Billing period ends {formatPaymentDate(sub.expires_at)}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2 shrink-0">
            {tier !== "super_standard" ? (
              <Link href="/pricing" className="btn btn-primary btn-sm">
                Upgrade plan
                <Icon name="arrowRight" size={14} />
              </Link>
            ) : (
              <Link href="/pricing" className="btn btn-outline btn-sm">
                View plans
              </Link>
            )}
            {tier !== "free" ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={cancelling}
                onClick={handleCancel}
              >
                {cancelling ? "Cancelling…" : "Cancel at period end"}
              </Button>
            ) : null}
          </div>
        </div>
        {tier !== "free" ? (
          <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
            To move to a lower paid tier, cancel at period end then choose a new plan on{" "}
            <Link href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              pricing
            </Link>
            . Prorated refunds: see{" "}
            <Link href="/legal/refund" className="underline" style={{ color: "var(--green-700)" }}>
              refund policy
            </Link>
            .
          </p>
        ) : null}
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
            No payment on file. Upgrade on the{" "}
            <Link href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              pricing page
            </Link>{" "}
            via Lenco mobile money or card.
          </p>
        )}
      </SettingsCard>

      <SettingsCard>
        <div className="eyebrow mb-2">Invoices</div>
        <InvoicePanel token={token!} payments={payments} onRefresh={reload} />
      </SettingsCard>
    </div>
  );
}
