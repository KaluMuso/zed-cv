import React from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Referrals | Admin",
};

export default function AdminReferralsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Referrals & Growth Engine</h1>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Manage referral rewards, payouts, and milestones.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border p-6" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
          <h3 className="font-semibold leading-none tracking-tight">Pending Payouts</h3>
          <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
            Coming soon: Ledger of users who reached the K50 cash reward milestone.
          </p>
        </div>
        
        <div className="rounded-xl border p-6" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
          <h3 className="font-semibold leading-none tracking-tight">Reward Configuration</h3>
          <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
            Coming soon: Edit the referral config thresholds (e.g., 10 signups = 2 matches).
          </p>
        </div>
      </div>
    </div>
  );
}
