import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "About",
  description:
    "ZedApply is built in Lusaka to help Zambian professionals find work faster — AI matching, tailored CVs, WhatsApp delivery.",
};

export default function AboutPage() {
  return (
    <main className="max-w-[860px] mx-auto px-5 sm:px-6 py-12 sm:py-16">
      <div className="eyebrow">§ Who we are</div>
      <h1
        className="font-display mt-2 mb-4"
        style={{
          fontSize: "clamp(36px, 6vw, 64px)",
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
        }}
      >
        Built in Zambia, for Zambian{" "}
        <span className="italic" style={{ color: "var(--copper-600)" }}>
          job seekers
        </span>
        .
      </h1>

      <p
        className="text-base sm:text-lg mb-10"
        style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
      >
        ZedApply is an AI job-matching platform for Zambian professionals.
        We aggregate roles from every active job board in the country,
        score them against your CV, and deliver the best matches to your
        WhatsApp — so you spend less time scrolling Facebook groups and
        more time interviewing.
      </p>

      {/* ── Mission ── */}
      <section className="card p-6 sm:p-8 mb-8">
        <div className="eyebrow mb-3" style={{ color: "var(--green-700)" }}>
          Our mission
        </div>
        <h2
          className="font-display mb-3"
          style={{ fontSize: 28, letterSpacing: "-0.01em" }}
        >
          Make every CV land where it actually fits.
        </h2>
        <p
          className="text-base"
          style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
        >
          Job search in Zambia is broken in a specific way: there&apos;s no
          shortage of qualified people, and there&apos;s no shortage of
          open roles — but the matching layer is missing. People apply to
          jobs they aren&apos;t ready for, employers wade through irrelevant
          applications, and good fits never meet. We&apos;re building the
          layer that closes that gap.
        </p>
      </section>

      {/* ── Why Zambia first ── */}
      <section className="card p-6 sm:p-8 mb-8">
        <div className="eyebrow mb-3" style={{ color: "var(--copper-600)" }}>
          Why Zambia first
        </div>
        <h2
          className="font-display mb-3"
          style={{ fontSize: 28, letterSpacing: "-0.01em" }}
        >
          Built for the way Zambians actually hire and apply.
        </h2>
        <ul
          className="list-none p-0 m-0 flex flex-col gap-4"
          style={{ color: "var(--ink-2)" }}
        >
          <li className="flex items-start gap-3">
            <span
              className="rounded-full inline-flex items-center justify-center shrink-0 mt-0.5"
              style={{
                width: 24,
                height: 24,
                background: "var(--green-100)",
                color: "var(--green-700)",
              }}
            >
              <Icon name="check" size={14} />
            </span>
            <span style={{ lineHeight: 1.7 }}>
              <strong>WhatsApp-first.</strong> Match alerts and tailored CVs
              land in the channel people actually check — no app to install,
              no inbox that fills with spam.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span
              className="rounded-full inline-flex items-center justify-center shrink-0 mt-0.5"
              style={{
                width: 24,
                height: 24,
                background: "var(--green-100)",
                color: "var(--green-700)",
              }}
            >
              <Icon name="check" size={14} />
            </span>
            <span style={{ lineHeight: 1.7 }}>
              <strong>Mobile money payments.</strong> MTN MoMo and Airtel
              Money, settled in ZMW. No card required.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span
              className="rounded-full inline-flex items-center justify-center shrink-0 mt-0.5"
              style={{
                width: 24,
                height: 24,
                background: "var(--green-100)",
                color: "var(--green-700)",
              }}
            >
              <Icon name="check" size={14} />
            </span>
            <span style={{ lineHeight: 1.7 }}>
              <strong>Local job feed.</strong> Every active Zambian board —
              Lusaka, Kitwe, Ndola, Solwezi, Livingstone, Chingola — plus
              direct partner postings. No reposted listings from other
              continents you can&apos;t legally apply to.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span
              className="rounded-full inline-flex items-center justify-center shrink-0 mt-0.5"
              style={{
                width: 24,
                height: 24,
                background: "var(--green-100)",
                color: "var(--green-700)",
              }}
            >
              <Icon name="check" size={14} />
            </span>
            <span style={{ lineHeight: 1.7 }}>
              <strong>Built locally.</strong> The team is in Lusaka and the
              data lives where Zambian data protection law applies.
            </span>
          </li>
        </ul>
      </section>

      {/* ── Founder note ── */}
      <section
        className="p-6 sm:p-8 mb-10 rounded-2xl"
        style={{
          background:
            "linear-gradient(135deg, var(--green-800) 0%, var(--green-700) 60%, var(--copper-700) 130%)",
          color: "#faf7f2",
        }}
      >
        <div
          className="eyebrow mb-3"
          style={{ color: "rgba(255,255,255,0.7)" }}
        >
          A note from the founder
        </div>
        <p
          className="font-display mb-4"
          style={{
            fontSize: "clamp(20px, 3vw, 26px)",
            lineHeight: 1.4,
            fontStyle: "italic",
          }}
        >
          &ldquo;I started ZedApply because I&apos;d watched too many
          friends apply for roles they were perfect for and never hear back —
          and too many recruiters drown in applications from people who
          weren&apos;t close. Computers are good at this kind of matching;
          people aren&apos;t. We just had to wire one up for Zambia.&rdquo;
        </p>
        <p
          className="text-sm"
          style={{ opacity: 0.85 }}
        >
          — Vergeo, Lusaka
        </p>
      </section>

      {/* ── CTA row ── */}
      <div className="flex flex-wrap gap-3 mb-10">
        <Link href="/pricing" className="btn btn-primary btn-lg">
          See pricing <Icon name="arrowRight" size={16} />
        </Link>
        <Link href="/contact" className="btn btn-ghost btn-lg">
          Contact us
        </Link>
      </div>
    </main>
  );
}
