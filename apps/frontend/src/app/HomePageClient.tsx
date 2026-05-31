"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FinalCtaSection } from "@/components/marketing/FinalCtaSection";
import { FourStepsSection } from "@/components/marketing/FourStepsSection";
import { HeroVisualComposition } from "@/components/marketing/HeroVisualComposition";
import { ScoreMathSection } from "@/components/marketing/ScoreMathSection";
import { TrustSection } from "@/components/marketing/TrustSection";
import { btnClass, surfaceCardClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { useAuth } from "@/lib/auth";
import { publicStats, type PublicStats } from "@/lib/api";
import { freeTierMatchesBlurb, freeTierFaqMatchExplanation } from "@/lib/tier-marketing";
import { AUTH_GET_STARTED } from "@/lib/auth-paths";

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
    blurb: `${freeTierMatchesBlurb()} + WhatsApp alerts`,
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
    a: "Yes. Cancel from your account settings — your paid features stay active until the end of your current billing period, and no further charges are made. New paid subscriptions also include a 7-day money-back guarantee if you have not used AI document generation — see our Refund Policy.",
  },
  {
    q: "Is it free?",
    a: `Yes. ${freeTierFaqMatchExplanation()} WhatsApp alerts and full job browsing are included on the Free tier. Paid tiers (K125–K500/month) unlock more matches and AI features like tailored CVs and cover letters.`,
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
                <Link href={primaryHref} className={btnClass("primary", "lg")}>
                  {primaryLabel} <Icon name="arrowRight" size={16} />
                </Link>
                <Link href="/jobs" className={btnClass("ghost", "lg")}>
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

            <HeroVisualComposition />
          </div>
        </div>
      </section>

      {/* ───────────────────── SOCIAL PROOF STRIP ───────────────────── */}
      <section
        className="section-below-fold"
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

      <FourStepsSection />

      <ScoreMathSection />

      {/* ─────────────────────── PRICING TEASER ─────────────────────── */}
      <section className="section-below-fold max-w-[1280px] mx-auto px-5 sm:px-6 py-16 sm:py-20 md:py-24">
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
              className={cn(surfaceCardClass, "card-hover job-card p-5 sm:p-6 reveal block")}
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

      <TrustSection />

      {/* ────────────────────────── FAQ ────────────────────────── */}
      <section
        className="section-below-fold"
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

      <FinalCtaSection primaryHref={primaryHref} />
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
    <div className={cn(surfaceCardClass, "divide-y")} style={{ borderColor: "var(--line)" }}>
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
