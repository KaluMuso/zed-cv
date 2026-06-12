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
import { MATCH_SCORE_FAQ_ANSWER } from "@/lib/matching-weights-copy";
import { freeTierMatchesBlurb, freeTierFaqMatchExplanation } from "@/lib/tier-marketing";
import { AUTH_GET_STARTED } from "@/lib/auth-paths";
import * as Accordion from "@radix-ui/react-accordion";
import { motion } from "framer-motion";

interface Plan {
  name: string;
  price: string;
  period: string;
  blurb: string;
  highlight: boolean;
}

// ── Page ──

export default function HomePageClient({ 
  initialFaqs = [], 
  initialTiers = [] 
}: { 
  initialFaqs?: any[]; 
  initialTiers?: any[] 
}) {
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

  // Map backend tiers to Plan shape
  const plans: Plan[] = initialTiers.map((t) => ({
    name: t.display_name,
    price: `K${Math.floor(t.price_ngwee / 100)}`,
    period: t.tier === "free" ? "forever" : "/month",
    blurb: t.marketing_blurb || "",
    highlight: !!t.is_highlighted,
  }));

  // Fallback plans if empty
  if (plans.length === 0) {
    plans.push(
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
        blurb: "50 matches + score breakdowns",
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
      }
    );
  }

  // Map backend FAQs to { q, a }
  let mappedFaqs = initialFaqs.map((f) => ({
    q: f.question,
    a: f.answer,
  }));

  if (mappedFaqs.length === 0) {
    mappedFaqs = [
      {
        q: "What's the matching score?",
        a: MATCH_SCORE_FAQ_ANSWER,
      },
      {
        q: "Is it free?",
        a: `Yes. ${freeTierFaqMatchExplanation()} WhatsApp alerts and full job browsing are included on the Free tier. Paid tiers (K125–K500/month) unlock more matches and AI features like tailored CVs and cover letters.`,
      },
      {
        q: "Where do the jobs come from?",
        a: "We aggregate roles from every active jobs board in Zambia plus direct postings from partner employers. Roles are deduplicated and quality-scored before they ever reach a match, so you don't see the same listing three times or pad your inbox with low-quality posts.",
      },
    ];
  }

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
              className="font-display mt-2 text-foreground"
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
            <motion.div
              key={p.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -4, scale: 1.01 }}
            >
              <Link
                href="/pricing"
                className={cn(surfaceCardClass, "card-hover job-card p-5 sm:p-6 block")}
                style={{
                  border: p.highlight
                    ? "1px solid var(--copper-400)"
                    : "1px solid rgba(255, 255, 255, 0.1)",
                  background: p.highlight 
                    ? "rgba(255, 255, 255, 0.05)" 
                    : "rgba(255, 255, 255, 0.02)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  position: "relative",
                  height: "100%",
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
            </motion.div>
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
            className="font-display mt-2 mb-8 sm:mb-10 text-foreground"
            style={{
              fontSize: "clamp(32px, 5vw, 60px)",
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            Questions, answered.
          </h2>

          <FaqList items={mappedFaqs} />
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
  return (
    <Accordion.Root 
      type="single" 
      collapsible 
      className={cn(surfaceCardClass, "divide-y overflow-hidden")} 
      style={{ 
        borderColor: "rgba(255, 255, 255, 0.1)",
        background: "rgba(255, 255, 255, 0.02)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      {items.map((item, i) => (
        <Accordion.Item 
          key={item.q} 
          value={`item-${i}`}
          className="border-b last:border-b-0"
          style={{ borderColor: "rgba(255, 255, 255, 0.1)" }}
        >
          <Accordion.Header className="flex">
            <Accordion.Trigger 
              className="w-full flex items-center justify-between gap-4 text-left px-5 sm:px-6 py-4 sm:py-5 group"
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "var(--ink)",
              }}
            >
              <span className="font-medium text-sm sm:text-base" style={{ lineHeight: 1.4 }}>
                {item.q}
              </span>
              <span 
                className="shrink-0 inline-flex items-center justify-center transition-transform duration-200 ease-in-out group-data-[state=open]:rotate-45 group-data-[state=open]:bg-[var(--green-100)] group-data-[state=open]:text-[var(--green-700)] group-data-[state=closed]:bg-[var(--bg-2)] group-data-[state=closed]:text-[var(--muted)]"
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 999,
                }}
              >
                <Icon name="plus" size={14} />
              </span>
            </Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Content 
            className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
          >
            <div className="px-5 sm:px-6 pb-5 text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>
              {item.a}
            </div>
          </Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
