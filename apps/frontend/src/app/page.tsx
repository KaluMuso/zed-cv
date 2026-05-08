"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { useAuth } from "@/lib/auth";

const stats = [
  { value: 542, suffix: "+", label: "Jobs matched" },
  { value: 2018, suffix: "+", label: "Job seekers" },
  { value: 85, suffix: "%", label: "Match accuracy" },
  { value: 30, suffix: "s", label: "Avg. first match" },
];

const howItWorks = [
  {
    n: "01",
    icon: "upload",
    title: "Upload your CV",
    description:
      "PDF, DOC, or photo. Our AI parses your skills, education and experience in seconds.",
  },
  {
    n: "02",
    icon: "sparkle",
    title: "AI scores every job",
    description:
      "6 boards. 542+ open roles. Each scored on relevance, skills overlap, and bonus signals.",
  },
  {
    n: "03",
    icon: "whatsapp",
    title: "Get pinged on WhatsApp",
    description:
      "Daily summary of your top 3 matches, plus apply links. No spam. Cancel anytime.",
  },
];

const scienceBullets: [string, string][] = [
  ["Relevance", "Career trajectory & seniority"],
  ["Skills overlap", "Matched vs missing competencies"],
  ["Local fit", "Location, salary band, work permit"],
];

const testimonials = [
  {
    name: "Mwila K.",
    role: "Junior Accountant, Lusaka",
    quote:
      "Three matches in week one. Got a callback from ZANACO before the weekend.",
    accent: "green",
  },
  {
    name: "Bwalya M.",
    role: "Software Developer, Ndola",
    quote:
      "I was applying blind on Facebook groups. Now WhatsApp pings me every morning with curated roles.",
    accent: "copper",
  },
  {
    name: "Natasha P.",
    role: "Marketing, Kitwe",
    quote:
      "The skill gap explanation showed me exactly what was missing from my CV. Updated it, scores went up.",
    accent: "green",
  },
];

const heroMatches: [string, string, number][] = [
  ["Senior Accountant", "ZANACO", 92],
  ["Software Developer", "MTN Zambia", 88],
  ["Logistics Coordinator", "Zambia Sugar", 68],
];

export default function HomePage() {
  useScrollReveal();
  const { isAuthenticated } = useAuth();

  return (
    <div>
      {/* ─── Hero ─── */}
      <section className="grain relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(80% 50% at 80% 0%, color-mix(in oklab, var(--copper-100) 60%, transparent) 0%, transparent 60%), radial-gradient(60% 40% at 0% 100%, color-mix(in oklab, var(--green-100) 70%, transparent) 0%, transparent 60%)",
          }}
        />
        <div className="relative max-w-[1280px] mx-auto px-6 pt-16 pb-24 md:pt-20">
          <div className="grid gap-12 lg:gap-16 lg:grid-cols-[1.1fr_1fr] items-center">
            {/* LEFT — copy */}
            <div className="fade-up">
              <div
                className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full"
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
                  Live across Lusaka, Kitwe, Solwezi & 6 more
                </span>
              </div>

              <h1
                className="font-display mt-7 leading-none"
                style={{
                  fontSize: "clamp(48px, 8vw, 96px)",
                  letterSpacing: "-0.025em",
                  color: "var(--ink)",
                }}
              >
                Your next job,
                <br />
                <span
                  className="italic"
                  style={{ color: "var(--copper-600)" }}
                >
                  matched
                </span>{" "}
                by AI —
                <br />
                delivered on
                <span className="relative inline-block ml-3.5">
                  <span
                    className="absolute"
                    style={{
                      inset: "0.05em -0.15em",
                      background: "var(--green-100)",
                      transform: "rotate(-1deg)",
                      borderRadius: 4,
                      zIndex: -1,
                    }}
                  />
                  <span> WhatsApp.</span>
                </span>
              </h1>

              <p
                className="mt-7 text-lg leading-relaxed max-w-[540px]"
                style={{ color: "var(--ink-2)" }}
              >
                Upload your CV. We scrape every Zambian job board, score the
                matches against your skills, and ping the best ones to your
                phone. K0 to start.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                {isAuthenticated ? (
                  <Link href="/matches" className="btn btn-primary btn-lg">
                    Go to Dashboard <Icon name="arrowRight" size={16} />
                  </Link>
                ) : (
                  <Link href="/auth" className="btn btn-primary btn-lg">
                    Start matching — 30 seconds <Icon name="arrowRight" size={16} />
                  </Link>
                )}
                <Link href="/jobs" className="btn btn-ghost btn-lg">
                  Browse jobs first
                </Link>
              </div>

              <div
                className="mt-7 flex items-center gap-3.5 text-sm"
                style={{ color: "var(--muted)" }}
              >
                <Icon name="whatsapp" size={16} />
                <span>WhatsApp OTP. No email. No password.</span>
              </div>
            </div>

            {/* RIGHT — stacked CV + WhatsApp card */}
            <div className="hidden lg:block relative h-[560px]">
              {/* Background dotted card */}
              <div
                className="dot-bg absolute"
                style={{
                  inset: "40px 0 40px 40px",
                  borderRadius: 24,
                  border: "1px solid var(--line)",
                }}
              />

              {/* CV preview card (back, rotated) */}
              <div
                className="card absolute"
                style={{
                  top: 24,
                  left: 0,
                  width: "70%",
                  padding: 24,
                  transform: "rotate(-2deg)",
                  boxShadow: "var(--shadow-lg)",
                }}
              >
                <div className="flex items-center gap-2.5 mb-4">
                  <span style={{ color: "var(--copper-500)" }}>
                    <Icon name="file" size={16} />
                  </span>
                  <span
                    className="mono text-[11px]"
                    style={{ color: "var(--muted)" }}
                  >
                    chanda_mwape_cv.pdf
                  </span>
                </div>
                <div
                  className="font-display"
                  style={{ fontSize: 26, lineHeight: 1.1, marginBottom: 6 }}
                >
                  Chanda Mwape
                </div>
                <div
                  className="text-[13px] mb-[18px]"
                  style={{ color: "var(--muted)" }}
                >
                  Financial Analyst &middot; Lusaka
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {["Python", "SQL", "Excel", "Modeling", "IFRS"].map((s) => (
                    <span key={s} className="tag tag-mono">
                      {s}
                    </span>
                  ))}
                </div>
                <div
                  className="mt-[18px] h-1 rounded overflow-hidden"
                  style={{ background: "var(--bg-2)" }}
                >
                  <div
                    className="h-full"
                    style={{
                      width: "78%",
                      background:
                        "linear-gradient(90deg, var(--green-500), var(--copper-500))",
                    }}
                  />
                </div>
                <div
                  className="mt-2 text-[11px] mono"
                  style={{ color: "var(--muted)" }}
                >
                  Profile 78% complete
                </div>
              </div>

              {/* WhatsApp match notification card (front) */}
              <div
                className="card absolute"
                style={{
                  bottom: 0,
                  right: 0,
                  width: "78%",
                  padding: 22,
                  transform: "rotate(1.5deg)",
                  boxShadow: "var(--shadow-lg)",
                  zIndex: 2,
                  background: "var(--surface)",
                }}
              >
                <div className="flex items-center gap-2.5 mb-3.5">
                  <div
                    className="rounded-lg flex items-center justify-center"
                    style={{
                      width: 28,
                      height: 28,
                      background: "#25D366",
                      color: "#fff",
                    }}
                  >
                    <Icon name="whatsapp" size={14} />
                  </div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    WhatsApp &middot; just now
                  </div>
                </div>
                <div
                  className="font-display"
                  style={{
                    fontSize: 22,
                    lineHeight: 1.25,
                    color: "var(--ink)",
                  }}
                >
                  3 new matches for you, Chanda.
                </div>
                <div className="mt-4 flex flex-col gap-2.5">
                  {heroMatches.map(([t, c, sc]) => (
                    <div
                      key={t}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-[10px]"
                      style={{ background: "var(--bg-2)" }}
                    >
                      <div className="flex-1">
                        <div className="text-[13px] font-semibold">{t}</div>
                        <div
                          className="text-[11px]"
                          style={{ color: "var(--muted)" }}
                        >
                          {c}
                        </div>
                      </div>
                      <span
                        className="mono text-xs font-semibold px-2 py-1 rounded"
                        style={{
                          background:
                            sc >= 85
                              ? "var(--green-100)"
                              : "var(--copper-100)",
                          color:
                            sc >= 85
                              ? "var(--green-700)"
                              : "var(--copper-600)",
                        }}
                      >
                        {sc}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Floating chevron accent */}
              <div className="absolute top-0 right-0 opacity-50">
                <ChevronMotif w={120} h={80} />
              </div>
            </div>
          </div>

          {/* Stats strip */}
          <div
            className="mt-20 py-7 grid grid-cols-2 md:grid-cols-4 gap-4"
            style={{
              borderTop: "1px solid var(--line)",
              borderBottom: "1px solid var(--line)",
            }}
          >
            {stats.map((s) => (
              <div key={s.label}>
                <div
                  className="font-display leading-none"
                  style={{
                    fontSize: "clamp(36px, 5vw, 56px)",
                    color: "var(--ink)",
                  }}
                >
                  <Counter to={s.value} suffix={s.suffix} />
                </div>
                <div className="eyebrow mt-2">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section className="max-w-[1280px] mx-auto px-6 py-20 md:py-24">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <div className="eyebrow">§ 01 / How it works</div>
            <h2
              className="font-display mt-2"
              style={{
                fontSize: "clamp(36px, 5vw, 64px)",
                letterSpacing: "-0.02em",
              }}
            >
              Three steps,{" "}
              <span className="italic" style={{ color: "var(--copper-600)" }}>
                thirty seconds
              </span>
              .
            </h2>
          </div>
          <div className="hidden md:block">
            <ChevronMotif w={180} h={56} />
          </div>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-5">
          {howItWorks.map((step, i) => (
            <div
              key={step.n}
              className="card card-hover p-7 reveal"
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <div className="flex items-start justify-between">
                <div
                  className="w-12 h-12 rounded-xl inline-flex items-center justify-center"
                  style={{
                    background: "var(--green-100)",
                    color: "var(--green-700)",
                  }}
                >
                  <Icon name={step.icon} size={20} />
                </div>
                <span
                  className="mono text-xs"
                  style={{ color: "var(--copper-500)" }}
                >
                  {step.n}
                </span>
              </div>
              <h3
                className="font-display mt-6 mb-2"
                style={{ fontSize: 28, letterSpacing: "-0.01em" }}
              >
                {step.title}
              </h3>
              <p
                className="text-sm leading-relaxed m-0"
                style={{ color: "var(--muted)" }}
              >
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Score Breakdown Showcase ─── */}
      <section
        style={{
          background: "var(--bg-2)",
          borderTop: "1px solid var(--line)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 py-20 md:py-24">
          <div className="grid gap-12 lg:gap-16 lg:grid-cols-2 items-center">
            <div>
              <div className="eyebrow">§ 02 / The science</div>
              <h2
                className="font-display mt-2 mb-6"
                style={{
                  fontSize: "clamp(36px, 5vw, 64px)",
                  letterSpacing: "-0.02em",
                }}
              >
                Not a keyword filter.{" "}
                <span
                  className="italic"
                  style={{ color: "var(--copper-600)" }}
                >
                  A score.
                </span>
              </h2>
              <p
                className="text-base leading-relaxed max-w-[500px]"
                style={{ color: "var(--ink-2)" }}
              >
                Every job is rated on three axes: how relevant the role is to
                your career history, how well your skills overlap, and bonus
                signals like location and salary fit. Transparent, explainable,
                and tuned for the Zambian market.
              </p>
              <ul className="mt-7 list-none p-0 flex flex-col gap-3.5">
                {scienceBullets.map(([k, v]) => (
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
              className="card p-8"
              style={{ boxShadow: "var(--shadow-md)" }}
            >
              <div className="flex items-start justify-between mb-5">
                <div>
                  <div
                    className="font-display"
                    style={{ fontSize: 24, lineHeight: 1.1 }}
                  >
                    Senior Accountant
                  </div>
                  <div
                    className="text-[13px] mt-0.5"
                    style={{ color: "var(--muted)" }}
                  >
                    ZANACO &middot; Lusaka
                  </div>
                </div>
                <ScoreRing score={92} size={84} stroke={7} />
              </div>
              <div className="flex flex-col gap-3.5 mt-2">
                {[
                  ["Relevance", 95, "green"] as const,
                  ["Skills overlap", 88, "copper"] as const,
                  ["Local fit", 92, "green"] as const,
                ].map(([k, v, tone]) => (
                  <div key={k}>
                    <div className="flex justify-between items-baseline mb-1.5">
                      <span
                        className="text-[13px]"
                        style={{ color: "var(--ink-2)" }}
                      >
                        {k}
                      </span>
                      <span
                        className="mono text-xs"
                        style={{ color: "var(--muted)" }}
                      >
                        {v}/100
                      </span>
                    </div>
                    <div
                      className="rounded-[3px] overflow-hidden"
                      style={{ height: 6, background: "var(--bg-2)" }}
                    >
                      <div
                        className="h-full rounded-[3px] transition-[width] duration-1000"
                        style={{
                          width: `${v}%`,
                          background:
                            tone === "green"
                              ? "var(--green-500)"
                              : "var(--copper-500)",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div
                className="mt-5 p-4 rounded-[10px]"
                style={{
                  background: "var(--green-50)",
                  border: "1px dashed var(--green-300)",
                }}
              >
                <div
                  className="eyebrow mb-1.5"
                  style={{ color: "var(--green-700)" }}
                >
                  Why this match
                </div>
                <div
                  className="text-[13px] leading-relaxed"
                  style={{ color: "var(--green-800)" }}
                >
                  Strong overlap on IFRS reporting and Excel modeling. Lusaka
                  location matches your profile. One missing skill: SAP — minor
                  for this role.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Testimonials ─── */}
      <section className="max-w-[1280px] mx-auto px-6 py-20 md:py-24">
        <div className="eyebrow">§ 03 / Voices</div>
        <h2
          className="font-display mt-2 mb-12 max-w-[800px]"
          style={{
            fontSize: "clamp(36px, 5vw, 64px)",
            letterSpacing: "-0.02em",
          }}
        >
          From CV upload to first interview, in{" "}
          <span className="italic" style={{ color: "var(--copper-600)" }}>
            11 days.
          </span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {testimonials.map((t, i) => (
            <div
              key={t.name}
              className="card p-7 flex flex-col reveal"
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <span style={{ color: "var(--copper-500)" }}>
                <Icon name="star" size={18} />
              </span>
              <p
                className="font-display my-5"
                style={{
                  fontSize: 22,
                  lineHeight: 1.4,
                  color: "var(--ink)",
                }}
              >
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="flex items-center gap-3 mt-auto">
                <div
                  className="rounded-full inline-flex items-center justify-center text-white font-semibold"
                  style={{
                    width: 40,
                    height: 40,
                    fontSize: 14,
                    background: `linear-gradient(135deg, ${t.accent === "copper" ? "var(--copper-500)" : "var(--green-700)"} 0%, var(--copper-500) 120%)`,
                  }}
                >
                  {t.name
                    .split(" ")
                    .map((w) => w[0])
                    .join("")}
                </div>
                <div>
                  <div className="text-sm font-semibold">{t.name}</div>
                  <div
                    className="text-[13px]"
                    style={{ color: "var(--muted)" }}
                  >
                    {t.role}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Final CTA ─── */}
      <section className="max-w-[1280px] mx-auto px-6 pb-24">
        <div
          className="grain relative overflow-hidden rounded-3xl"
          style={{
            padding: "64px 48px",
            background:
              "linear-gradient(135deg, var(--green-800) 0%, var(--green-700) 60%, var(--copper-600) 130%)",
            color: "#faf7f2",
          }}
        >
          <div
            className="absolute hidden md:block"
            style={{ right: -40, top: -40, opacity: 0.18 }}
          >
            <ChevronMotif w={420} h={400} />
          </div>
          <div className="relative">
            <div
              className="eyebrow"
              style={{ color: "rgba(255,255,255,0.7)" }}
            >
              § Final note
            </div>
            <h2
              className="font-display mt-3 max-w-[800px]"
              style={{
                fontSize: "clamp(40px, 6vw, 80px)",
                letterSpacing: "-0.02em",
              }}
            >
              Stop scrolling Facebook groups.{" "}
              <span className="italic" style={{ color: "var(--copper-300)" }}>
                Start matching.
              </span>
            </h2>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href={isAuthenticated ? "/matches" : "/auth"}
                className="btn btn-lg"
                style={{
                  background: "#faf7f2",
                  color: "var(--green-800)",
                  fontWeight: 600,
                }}
              >
                {isAuthenticated
                  ? "Go to Dashboard"
                  : "Get started — K0 forever"}{" "}
                <Icon name="arrowRight" size={16} />
              </Link>
              <Link
                href="/pricing"
                className="btn btn-lg"
                style={{
                  background: "transparent",
                  color: "#faf7f2",
                  border: "1px solid rgba(255,255,255,0.3)",
                }}
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
