"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { useAuth } from "@/lib/auth";
import { publicStats, type PublicStats } from "@/lib/api";
import { FloatingCard } from "@/components/shared/FloatingCard";
import { cn } from "@/lib/utils";

// ── Static content ──

const howItWorks = [
  {
    n: "01",
    icon: "upload",
    title: "Upload your CV",
    description:
      "PDF, DOC, or photo. We extract skills, experience, location in seconds.",
  },
  {
    n: "02",
    icon: "sparkle",
    title: "AI scores every job",
    description:
      "Hybrid match: 60% semantic similarity + 30% skills overlap + 10% bonus signals.",
  },
  {
    n: "03",
    icon: "external",
    title: "Multi-channel apply",
    description:
      "Email, WhatsApp, phone, or website — whichever the employer accepts.",
  },
  {
    n: "04",
    icon: "whatsapp",
    title: "Daily WhatsApp digest",
    description:
      "Top 3 matches at 07:00. Reply YES to apply. No spam, no scrolling.",
  },
];

const matchAnnotations: [string, string][] = [
  ["Score", "0–100, transparent breakdown"],
  ["Skills", "Matched + missing called out"],
  ["Why", "Plain-English explanation"],
];

interface Plan {
  name: string;
  price: string;
  period: string;
  blurb: string;
  highlight: boolean;
}

const plans: Plan[] = [
  {
    name: "Free",
    price: "K0",
    period: "forever",
    blurb: "10 matches/month + WhatsApp alerts",
    highlight: false,
  },
  {
    name: "Starter",
    price: "K125",
    period: "/month",
    blurb: "50 matches + tailored CVs",
    highlight: true,
  },
  {
    name: "Professional",
    price: "K250",
    period: "/month",
    blurb: "125 matches + cover letters",
    highlight: false,
  },
  {
    name: "Super Standard",
    price: "K500",
    period: "/month",
    blurb: "Unlimited matches + interview prep",
    highlight: false,
  },
];

const faqs: { q: string; a: React.ReactNode }[] = [
  {
    q: "What's the matching score?",
    a: "Every job gets a 0–100 score from your CV. It's a blend of three signals: vector similarity between your CV and the job description (60%), how your skills overlap with what the role asks for (30%), and bonus signals like location and salary band (10%). Each match shows you the full breakdown.",
  },
  {
    q: "Do you send my CV anywhere?",
    a: (
      <>
        No. Your CV stays on our servers and is only used to score matches and
        generate tailored CVs <em>for you</em>. We never share it with employers
        or third parties without your explicit consent. See our{" "}
        <Link
          href="/legal/privacy"
          style={{ color: "var(--green-700)", textDecoration: "underline" }}
        >
          Privacy Policy
        </Link>{" "}
        for the full notice.
      </>
    ),
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Cancel from your account settings — your paid features stay active until the end of your current billing period, and no further charges are made. New ZedApply subscriptions also come with a 14-day money-back guarantee on the first paid month.",
  },
  {
    q: "Is it free?",
    a: "Yes. The Free tier gives you 10 matches per month, WhatsApp alerts, and full job browsing — forever. Paid tiers (K125–K500/month) unlock more matches and AI features like tailored CVs and cover letters.",
  },
  {
    q: "Where do the jobs come from?",
    a: "We aggregate roles from every active jobs board in Zambia plus direct postings from partner employers. Roles are deduplicated and quality-scored before they ever reach a match, so you don't see the same listing three times or pad your inbox with low-quality posts.",
  },
  {
    q: "When are matches sent?",
    a: "WhatsApp digests go out once per day (typically 07:30 CAT) with your top three new matches. Anything urgent — a high-score match on a fresh listing — pings the same day. You can also see every match the moment it's scored in your dashboard.",
  },
  {
    q: "How is my data protected?",
    a: (
      <>
        TLS in transit, encryption at rest, WhatsApp OTP sign-in (no password to
        leak or phish), and strict access controls inside our team. We comply
        with the Zambia Data Protection Act 2021. You can export or delete your
        data at any time — see the{" "}
        <Link
          href="/legal/privacy"
          style={{ color: "var(--green-700)", textDecoration: "underline" }}
        >
          Privacy Policy
        </Link>
        .
      </>
    ),
  },
  {
    q: "Do I need to be in Lusaka?",
    a: "No. We carry roles from across Zambia — Lusaka, Kitwe, Ndola, Solwezi, Livingstone, Chingola and more — plus remote roles open to Zambian residents. Your location is one signal in the score, not a hard filter.",
  },
];

// ── Page ──

export default function HomePageClient() {
  useScrollReveal();
  const { isAuthenticated } = useAuth();
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [statsLoaded, setStatsLoaded] = useState(false);

  useEffect(() => {
    publicStats
      .get()
      .then((s) => setStats(s))
      .catch(() => setStats(null))
      .finally(() => setStatsLoaded(true));
  }, []);

  const primaryHref = isAuthenticated ? "/matches" : "/auth";
  const primaryLabel = isAuthenticated ? "Go to dashboard" : "Get matched";

  return (
    <div>
      {/* ─────────────────────────── HERO ─────────────────────────── */}
      <section className="grain relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(80% 50% at 80% 0%, color-mix(in oklab, var(--copper-100) 60%, transparent) 0%, transparent 60%), radial-gradient(60% 40% at 0% 100%, color-mix(in oklab, var(--green-100) 70%, transparent) 0%, transparent 60%)",
          }}
        />
        <div className="relative max-w-[1280px] mx-auto px-5 sm:px-6 pt-12 sm:pt-16 pb-16 sm:pb-20 md:pt-20">
          <div className="grid gap-10 lg:gap-16 lg:grid-cols-[1.1fr_1fr] items-center">
            {/* LEFT — copy */}
            <div className="fade-up">
              <div
                className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--line)",
                }}
              >
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{
                    background: "var(--green-500)",
                    boxShadow:
                      "0 0 0 4px color-mix(in oklab, var(--green-500) 25%, transparent)",
                  }}
                />
                <span
                  className="text-xs font-medium"
                  style={{ color: "var(--ink-2)" }}
                >
                  Live across Lusaka, Kitwe, Solwezi &amp; 6 more
                </span>
              </div>

              <h1
                className="font-display mt-6 sm:mt-7"
                style={{
                  fontSize: "clamp(40px, 7vw, 84px)",
                  lineHeight: 1.02,
                  letterSpacing: "-0.025em",
                  color: "var(--ink)",
                }}
              >
                AI job matching for{" "}
                <span className="italic" style={{ color: "var(--copper-600)" }}>
                  Zambian professionals
                </span>
                .
              </h1>

              <p
                className="mt-6 text-base sm:text-lg leading-relaxed max-w-[560px]"
                style={{ color: "var(--ink-2)" }}
              >
                Built on the country&apos;s largest aggregated jobs feed, with
                tailored CVs and WhatsApp delivery. Every job gets a{" "}
                <strong style={{ color: "var(--ink)" }}>0–100 score</strong>{" "}
                from your CV — skill overlap, career fit, and local signals,
                all explained.
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                <Link href={primaryHref} className="btn btn-primary btn-lg">
                  {primaryLabel} <Icon name="arrowRight" size={16} />
                </Link>
                <Link href="/jobs" className="btn btn-ghost btn-lg">
                  Browse jobs
                </Link>
              </div>

              <div
                className="mt-6 flex items-center gap-3 text-sm"
                style={{ color: "var(--muted)" }}
              >
                <Icon name="whatsapp" size={16} />
                <span>WhatsApp OTP. No email. No password.</span>
              </div>
            </div>

            {/* RIGHT — WhatsApp-style floating digest card */}
            <div className="flex justify-center lg:justify-end">
              <FloatingCard>
              <div
                className="w-full max-w-sm rounded-xl border border-white/10 bg-surface-dark p-4 shadow-raised ring-1 ring-white/5 sm:max-w-sm sm:p-5"
                role="img"
                aria-label="WhatsApp digest preview: Good morning Chanda, 3 new matches"
              >
                <div className="flex items-center gap-2.5 mb-4">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#25D366] text-white">
                    <Icon name="whatsapp" size={16} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-[#8696a0]">
                      ZedApply
                    </div>
                    <div className="text-[10px] text-[#667781]">07:00</div>
                  </div>
                </div>
                <p className="text-[15px] sm:text-base font-medium leading-snug text-[#e9edef]">
                  Good morning Chanda! 3 new matches:
                </p>
                <ul className="mt-4 flex flex-col gap-2">
                  {(
                    [
                      ["Senior Accountant", "ZANACO", 92],
                      ["Frontend Engineer", "MTN", 88],
                    ] as [string, string, number][]
                  ).map(([title, company, score]) => (
                    <li
                      key={title}
                      className="flex items-center justify-between gap-2 rounded-xl bg-[#1f2c34] px-3 py-2.5"
                    >
                      <span className="min-w-0 text-[13px] text-[#d1d7db] truncate">
                        <span className="font-semibold text-[#e9edef]">
                          {title}
                        </span>
                        <span className="text-[#8696a0]"> · {company}</span>
                        <span className="text-[#25D366]"> ({score}%)</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              </FloatingCard>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────── SOCIAL PROOF STRIP ───────────────────── */}
      <section
        style={{
          borderTop: "1px solid var(--line)",
          borderBottom: "1px solid var(--line)",
          background: "var(--surface)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-10 sm:py-12">
          <div className="eyebrow text-center mb-6">
            Live numbers across the platform
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
            <SocialProofCard
              loaded={statsLoaded}
              value={stats?.jobs_active}
              suffix="+"
              label="Jobs aggregated"
              hint="Live across every active Zambian board"
              fallback="500+"
            />
            <SocialProofCard
              loaded={statsLoaded}
              value={stats?.avg_skills_matched}
              suffix=""
              label="Skills matched per user on average"
              hint="Across vector + skill-overlap scoring"
              fallback="7"
            />
            <SocialProofCard
              loaded={statsLoaded}
              value={stats?.hours_saved_total}
              suffix="+"
              label="Hours saved across applicants"
              hint="Half an hour saved per delivered match"
              fallback="1,000+"
            />
          </div>
        </div>
      </section>

      {/* ────────────────────── HOW IT WORKS ────────────────────── */}
      <section
        id="how-it-works"
        className="bg-slate-950 border-y border-slate-800/80"
      >
        <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
          <div className="text-center max-w-2xl mx-auto">
            <div className="eyebrow text-emerald-400/90">§ 01 / How it works</div>
            <h2 className="font-serif font-display mt-3 text-3xl sm:text-4xl md:text-5xl leading-tight tracking-tight text-slate-50">
              Four steps. One coffee.
            </h2>
          </div>

          <div className="mt-10 sm:mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
            {howItWorks.map((step, i) => (
              <div
                key={step.n}
                className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 sm:p-7 reveal transition-shadow hover:shadow-lg hover:shadow-black/20"
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                <div className="flex items-start justify-between">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                    <Icon name={step.icon} size={20} />
                  </div>
                  <span className="font-mono text-xs text-amber-500/90">
                    {step.n}
                  </span>
                </div>
                <h3 className="font-display mt-5 sm:mt-6 mb-2 text-xl text-slate-50">
                  {step.title}
                </h3>
                <p className="m-0 text-sm leading-relaxed text-slate-400">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ───────────── TRANSPARENT SCORING ───────────── */}
      <section
        style={{
          background: "var(--bg-2)",
          borderTop: "1px solid var(--line)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
          <div className="grid gap-10 lg:gap-16 lg:grid-cols-2 items-center">
            <div>
              <div className="eyebrow">§ 02 / Transparent scoring</div>
              <h2
                className="font-display mt-2 mb-5"
                style={{
                  fontSize: "clamp(32px, 5vw, 60px)",
                  lineHeight: 1.05,
                  letterSpacing: "-0.02em",
                }}
              >
                Every match shows{" "}
                <span
                  className="italic text-emerald-600 dark:text-emerald-400"
                >
                  its math
                </span>
                .
              </h2>
              <p
                className="text-base leading-relaxed max-w-[520px] text-ink-2"
                style={{ color: "var(--ink-2)" }}
              >
                No black box. Every score breaks down into three components,
                and the AI writes a one-paragraph explanation in plain English
                — like a recruiter would.
              </p>
              <ul className="mt-7 list-none p-0 flex flex-col gap-3.5">
                {matchAnnotations.map(([k, v]) => (
                  <li key={k} className="flex items-start gap-3.5">
                    <div
                      className="rounded-full inline-flex items-center justify-center flex-shrink-0 mt-0.5"
                      style={{
                        width: 24,
                        height: 24,
                        background: "var(--green-100)",
                        color: "var(--green-700)",
                      }}
                    >
                      <Icon name="check" size={14} />
                    </div>
                    <div>
                      <div className="font-semibold">{k}</div>
                      <div
                        className="text-sm"
                        style={{ color: "var(--muted)" }}
                      >
                        {v}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Score card mockup */}
            <div
              className="card p-6 sm:p-8 dark:bg-card dark:border-border"
              style={{ boxShadow: "var(--shadow-md)" }}
            >
              <div className="flex items-start justify-between mb-5 gap-3">
                <div className="min-w-0">
                  <div
                    className="font-display text-foreground"
                    style={{ fontSize: 22, lineHeight: 1.1 }}
                  >
                    Senior Accountant
                  </div>
                  <div className="text-[13px] mt-0.5 text-muted-foreground">
                    ZANACO &middot; Lusaka
                  </div>
                </div>
                <ScoreRing score={92} size={80} stroke={7} />
              </div>
              <div className="flex flex-col gap-3.5 mt-2">
                {(
                  [
                    ["Semantic similarity", 60, "bg-emerald-500"],
                    ["Skills overlap", 30, "bg-amber-500"],
                    ["Bonus signals", 10, "bg-slate-400"],
                  ] as [string, number, string][]
                ).map(([label, pct, barClass]) => (
                  <div key={label}>
                    <div className="flex justify-between items-baseline mb-1.5">
                      <span className="text-[13px] text-ink-2 dark:text-muted-foreground">
                        {label}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {pct}%
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden bg-bg-2 dark:bg-muted/30">
                      <div
                        className={cn("h-full rounded-full transition-[width] duration-1000 ease-out", barClass)}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-5 rounded-xl border border-border bg-muted/40 p-4 dark:bg-muted/20">
                <div className="eyebrow mb-1.5 text-emerald-700 dark:text-emerald-400">
                  AI explanation
                </div>
                <p className="m-0 text-[13px] leading-relaxed text-foreground dark:text-gray-200">
                  Strong overlap on IFRS reporting and Excel modeling. Lusaka
                  location matches your profile. One missing skill: SAP — minor
                  for this role.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────── PRICING TEASER ─────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
        <div className="flex flex-wrap items-baseline justify-between gap-4 mb-10">
          <div>
            <div className="eyebrow">§ 03 / Pricing</div>
            <h2
              className="font-display mt-2"
              style={{
                fontSize: "clamp(32px, 5vw, 60px)",
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
              }}
            >
              Free forever.{" "}
              <span className="italic" style={{ color: "var(--copper-600)" }}>
                Paid when you need more.
              </span>
            </h2>
          </div>
          <Link
            href="/pricing"
            className="text-sm font-medium"
            style={{
              color: "var(--green-700)",
              textDecoration: "underline",
            }}
          >
            Compare plans →
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((p, i) => (
            <Link
              key={p.name}
              href="/pricing"
              className="card card-hover p-5 sm:p-6 reveal block"
              style={{
                transitionDelay: `${i * 75}ms`,
                border: p.highlight
                  ? "1px solid var(--copper-400)"
                  : "1px solid var(--line)",
                background: p.highlight ? "var(--surface)" : "var(--surface)",
                position: "relative",
              }}
            >
              {p.highlight && (
                <span
                  className="absolute mono text-[10px] font-semibold px-2 py-1 rounded-full"
                  style={{
                    top: -10,
                    left: 16,
                    background: "var(--copper-500)",
                    color: "#fff",
                    letterSpacing: "0.05em",
                  }}
                >
                  POPULAR
                </span>
              )}
              <div
                className="eyebrow mb-2"
                style={{ color: "var(--muted)" }}
              >
                {p.name}
              </div>
              <div className="flex items-baseline gap-1 mb-3">
                <span
                  className="font-display"
                  style={{
                    fontSize: 36,
                    lineHeight: 1,
                    letterSpacing: "-0.02em",
                    color: "var(--ink)",
                  }}
                >
                  {p.price}
                </span>
                <span
                  className="text-xs"
                  style={{ color: "var(--muted)" }}
                >
                  {p.period}
                </span>
              </div>
              <p
                className="text-sm leading-relaxed m-0"
                style={{ color: "var(--ink-2)" }}
              >
                {p.blurb}
              </p>
              <div
                className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium"
                style={{ color: "var(--green-700)" }}
              >
                See details <Icon name="arrowRight" size={12} />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ────────────────────────── FAQ ────────────────────────── */}
      <section
        style={{
          background: "var(--bg-2)",
          borderTop: "1px solid var(--line)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="max-w-[920px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
          <div className="eyebrow">§ 04 / FAQ</div>
          <h2
            className="font-display mt-2 mb-8 sm:mb-10"
            style={{
              fontSize: "clamp(32px, 5vw, 60px)",
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            Questions, answered.
          </h2>

          <FaqList items={faqs} />
        </div>
      </section>

      {/* ────────────────────── FINAL CTA ────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
        <div className="grain relative overflow-hidden rounded-2xl sm:rounded-3xl bg-gradient-to-r from-emerald-600 to-green-500 px-6 py-10 sm:px-10 sm:py-14 text-white">
          <div
            className="absolute hidden md:block"
            style={{ right: -40, top: -40, opacity: 0.18 }}
          >
            <ChevronMotif w={420} h={400} />
          </div>
          <div className="relative">
            <div className="eyebrow text-white/70">§ Final note</div>
            <h2
              className="font-display mt-3 max-w-[800px]"
              style={{
                fontSize: "clamp(28px, 5vw, 56px)",
                lineHeight: 1.08,
                letterSpacing: "-0.02em",
              }}
            >
              Your next role is already in our database.
            </h2>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href={primaryHref}
                className="btn btn-lg bg-white text-emerald-800 font-semibold hover:bg-white/90"
              >
                {primaryLabel} <Icon name="arrowRight" size={16} />
              </Link>
              <Link
                href="/pricing"
                className="btn btn-lg border border-white/30 bg-transparent text-white hover:bg-white/10"
              >
                See pricing
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// ── Components ──

function SocialProofCard({
  loaded,
  value,
  suffix,
  label,
  hint,
  fallback,
}: {
  loaded: boolean;
  value: number | undefined;
  suffix: string;
  label: string;
  hint: string;
  fallback: string;
}) {
  // Three display states: skeleton (loading), real number (loaded + value),
  // fallback copy (loaded but API failed). The fallback never reads "0";
  // we'd rather show a sensible-looking estimate than zero on a marketing
  // page during a backend hiccup.
  const showSkeleton = !loaded;
  const hasNumber = loaded && typeof value === "number" && value > 0;

  return (
    <div
      className="p-5 sm:p-6 rounded-2xl"
      style={{
        background: "var(--bg)",
        border: "1px solid var(--line)",
      }}
    >
      <div
        className="font-display leading-none"
        style={{
          fontSize: "clamp(36px, 5vw, 56px)",
          letterSpacing: "-0.02em",
          color: "var(--ink)",
          minHeight: "1em",
        }}
      >
        {showSkeleton ? (
          <span
            className="inline-block rounded-md"
            style={{
              width: "5ch",
              height: "0.85em",
              background: "var(--bg-2)",
              animation: "shimmer 1.4s linear infinite",
              backgroundImage:
                "linear-gradient(90deg, var(--bg-2) 0%, var(--line) 50%, var(--bg-2) 100%)",
              backgroundSize: "400px 100%",
            }}
            aria-hidden
          />
        ) : hasNumber ? (
          <Counter to={value as number} suffix={suffix} />
        ) : (
          <span>{fallback}</span>
        )}
      </div>
      <div className="eyebrow mt-3" style={{ color: "var(--ink-2)" }}>
        {label}
      </div>
      <div
        className="text-xs mt-1.5"
        style={{ color: "var(--muted)" }}
      >
        {hint}
      </div>
    </div>
  );
}

function FaqList({
  items,
}: {
  items: { q: string; a: React.ReactNode }[];
}) {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="card divide-y" style={{ borderColor: "var(--line)" }}>
      {items.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q} style={{ borderColor: "var(--line)" }}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : i)}
              aria-expanded={isOpen}
              className="w-full flex items-center justify-between gap-4 text-left px-5 sm:px-6 py-4 sm:py-5"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--ink)",
              }}
            >
              <span
                className="font-medium text-sm sm:text-base"
                style={{ lineHeight: 1.4 }}
              >
                {item.q}
              </span>
              <span
                className="shrink-0 inline-flex items-center justify-center"
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 999,
                  background: isOpen ? "var(--green-100)" : "var(--bg-2)",
                  color: isOpen ? "var(--green-700)" : "var(--muted)",
                  transition: "all 200ms ease",
                  transform: isOpen ? "rotate(45deg)" : "rotate(0deg)",
                }}
                aria-hidden
              >
                <Icon name="plus" size={14} />
              </span>
            </button>
            {isOpen && (
              <div
                className="px-5 sm:px-6 pb-5 text-sm leading-relaxed"
                style={{ color: "var(--ink-2)" }}
              >
                {item.a}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
