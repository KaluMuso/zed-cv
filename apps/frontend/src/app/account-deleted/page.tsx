import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Account deleted",
  description:
    "Your ZedApply account has been deleted. Here is what was removed and what we are required to keep.",
  robots: { index: false, follow: false },
};

export default function AccountDeletedPage() {
  return (
    <main className="max-w-2xl mx-auto px-5 sm:px-6 py-12 sm:py-20">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
        style={{ background: "var(--green-100)", color: "var(--green-700)" }}
      >
        <Icon name="check" size={28} />
      </div>

      <h1
        className="font-display mb-3"
        style={{
          fontSize: "clamp(36px, 5vw, 56px)",
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
        }}
      >
        Your account is gone.
      </h1>
      <p
        className="text-base mb-8"
        style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
      >
        We&apos;ve deleted your ZedApply account. Thanks for trying us —
        sorry to see you go. Here&apos;s exactly what happened to your data.
      </p>

      <section className="card p-6 mb-6">
        <h2
          className="font-display mb-3"
          style={{ fontSize: 22, color: "var(--copper-600)" }}
        >
          What we removed
        </h2>
        <ul
          className="list-disc pl-5 space-y-2 text-sm"
          style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
        >
          <li>Your profile (name, email, location, preferences)</li>
          <li>Every CV you uploaded — both the file in storage and the parsed text</li>
          <li>Every AI-generated CV we produced for you</li>
          <li>Your match history, saved skills and application activity</li>
          <li>One-time WhatsApp passcodes tied to your phone number</li>
        </ul>
      </section>

      <section className="card p-6 mb-8">
        <h2
          className="font-display mb-3"
          style={{ fontSize: 22, color: "var(--copper-600)" }}
        >
          What we are required to keep
        </h2>
        <p
          className="text-sm mb-3"
          style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
        >
          Zambian tax law requires us to retain financial records for
          <strong> 7 years</strong>. So we&apos;ve kept the following,
          <strong> anonymised</strong> — no longer linked to your name,
          phone, or account:
        </p>
        <ul
          className="list-disc pl-5 space-y-2 text-sm"
          style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
        >
          <li>Subscription records (tier, period, amount)</li>
          <li>Payment records (amount, currency, method, transaction reference)</li>
        </ul>
        <p
          className="text-xs mt-4"
          style={{ color: "var(--muted)" }}
        >
          For full details, see our{" "}
          <Link
            href="/legal/privacy"
            style={{ color: "var(--green-700)", textDecoration: "underline" }}
          >
            Privacy Policy
          </Link>
          .
        </p>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link href="/" className="btn btn-primary">
          Back to home <Icon name="arrowRight" size={14} />
        </Link>
        <Link href="/auth" className="btn btn-ghost">
          Create a new account
        </Link>
      </div>
    </main>
  );
}
