"use client";

import Script from "next/script";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { employer, type EmployerSubscription, type EmployerTier } from "@/lib/api";
import { profile } from "@/lib/api";

const LENCO_SCRIPT =
  process.env.NEXT_PUBLIC_LENCO_SCRIPT_URL ?? "https://pay.sandbox.lenco.co/js/v1/inline.js";

function kwacha(ngwee: number) {
  return ngwee / 100;
}

export default function EmployerBillingPage() {
  const { token, user } = useAuth();
  const [sub, setSub] = useState<EmployerSubscription | null>(null);
  const [lencoReady, setLencoReady] = useState(false);
  const [paying, setPaying] = useState<EmployerTier | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!token) return;
    void employer.subscription(token).then(setSub);
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function startCheckout(tier: EmployerTier) {
    if (!token || !window.LencoPay) return;
    setPaying(tier);
    setMessage(null);
    try {
      const checkout = await employer.checkout(token, tier);
      const prof = await profile.get(token).catch(() => null);
      const email =
        prof?.email?.trim() || `employer+${user?.id?.slice(0, 8) ?? "user"}@zedapply.com`;

      window.label = checkout.label;
      window.LencoPay.getPaid({
        key: checkout.public_key,
        label: checkout.label,
        reference: checkout.reference,
        email,
        amount: kwacha(checkout.amount_ngwee),
        currency: "ZMW",
        channels: ["card", "mobile-money"],
        onSuccess: async (response: { reference: string }) => {
          try {
            const result = await employer.verifyPayment(token, {
              reference: response.reference,
              tier,
            });
            setMessage(result.message);
            refresh();
          } catch (err) {
            setMessage(err instanceof Error ? err.message : "Verification failed");
          } finally {
            setPaying(null);
          }
        },
        onClose: () => setPaying(null),
      });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Checkout failed");
      setPaying(null);
    }
  }

  return (
    <div className="space-y-6">
      <Script src={LENCO_SCRIPT} onLoad={() => setLencoReady(true)} strategy="afterInteractive" />
      {sub?.active ? (
        <p className="text-sm">
          Active: <strong>{sub.tier === "pro" ? "Employer Pro" : "Employer Lite"}</strong> —{" "}
          {sub.contacts_used}/{sub.contacts_limit >= 99999 ? "∞" : sub.contacts_limit} contacts
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">Choose a plan to search and contact candidates.</p>
      )}
      <div className="grid sm:grid-cols-2 gap-4 max-w-2xl">
        <div className="rounded-lg border p-4">
          <h3 className="font-medium">Employer Lite</h3>
          <p className="text-xl font-bold mt-1">K500/mo</p>
          <p className="text-xs text-muted-foreground mt-1">5 contacts per month</p>
          <button
            type="button"
            disabled={!lencoReady || paying !== null}
            className="mt-4 w-full rounded-lg bg-primary text-primary-foreground py-2 text-sm disabled:opacity-50"
            onClick={() => void startCheckout("lite")}
          >
            {paying === "lite" ? "Opening…" : "Subscribe"}
          </button>
        </div>
        <div className="rounded-lg border border-primary p-4">
          <h3 className="font-medium">Employer Pro</h3>
          <p className="text-xl font-bold mt-1">K2,500/mo</p>
          <p className="text-xs text-muted-foreground mt-1">Unlimited contacts</p>
          <button
            type="button"
            disabled={!lencoReady || paying !== null}
            className="mt-4 w-full rounded-lg bg-primary text-primary-foreground py-2 text-sm disabled:opacity-50"
            onClick={() => void startCheckout("pro")}
          >
            {paying === "pro" ? "Opening…" : "Subscribe"}
          </button>
        </div>
      </div>
      {message ? <p className="text-sm">{message}</p> : null}
    </div>
  );
}
