"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { ChevronMotif } from "@/components/ui/ChevronMotif";

const stats = [
  { value: 542, suffix: "+", label: "Jobs matched" },
  { value: 2018, suffix: "+", label: "Job seekers" },
  { value: 85, suffix: "%", label: "Match accuracy" },
  { value: 30, suffix: "s", label: "Avg. first match" },
];

const howItWorks = [
  {
    icon: "upload",
    title: "Upload your CV",
    description:
      "Drop your CV in PDF, Word, or even snap a photo. Our AI extracts your skills, experience, and career trajectory.",
  },
  {
    icon: "target",
    title: "Get scored matches",
    description:
      "We score every Zambian job listing against your profile. See exactly why each role fits — and where the gaps are.",
  },
  {
    icon: "whatsapp",
    title: "Receive on WhatsApp",
    description:
      "Top matches land in your WhatsApp every morning. Reply to get a tailored CV or cover letter on the spot.",
  },
];

const testimonials = [
  {
    quote:
      "I uploaded my CV at 8 PM and by 9 AM I had three interviews lined up. The matching is genuinely smart.",
    name: "Chanda Mwape",
    role: "Accountant, Lusaka",
  },
  {
    quote:
      "The tailored CVs are a game-changer. Each one highlights exactly what the employer is looking for.",
    name: "Bwalya Mutale",
    role: "Software Developer, Kitwe",
  },
  {
    quote:
      "WhatsApp delivery means I never miss a deadline. It feels like having a personal career assistant.",
    name: "Mwila Banda",
    role: "Nurse, Ndola",
  },
];

export default function HomePage() {
  return (
    <div>
      {/* ─── Hero ─── */}
      <section
        className="relative overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, var(--green-100) 0%, var(--bg) 70%)",
        }}
      >
        <div className="grain" style={{ position: "absolute", inset: 0, opacity: 0.4 }} />
        <div
          className="absolute -top-20 -right-20 opacity-20 hidden lg:block"
          style={{ zIndex: 0 }}
        >
          <ChevronMotif w={500} h={350} />
        </div>

        <div className="relative z-10 max-w-[1280px] mx-auto px-6 pt-16 pb-20 md:pt-24 md:pb-28">
          <div className="max-w-3xl">
            <div className="eyebrow mb-4">AI-powered job matching</div>
            <h1
              className="font-display leading-[0.95] tracking-tight"
              style={{
                fontSize: "clamp(44px, 7vw, 88px)",
                letterSpacing: "-0.03em",
              }}
            >
              Find your perfect
              <br />
              <span className="italic" style={{ color: "var(--copper-500)" }}>
                match
              </span>{" "}
              in Zambia.
            </h1>
            <p
              className="mt-6 text-base md:text-lg leading-relaxed max-w-xl"
              style={{ color: "var(--muted)" }}
            >
              Upload your CV and let AI score you against every open role in
              Zambia. Get matches on WhatsApp, tailored CVs per job, and land
              interviews faster.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mt-8">
              <Link href="/auth" className="btn btn-primary btn-lg">
                Get Started Free <Icon name="arrowRight" size={16} />
              </Link>
              <Link href="/pricing" className="btn btn-ghost btn-lg">
                View Plans
              </Link>
            </div>
          </div>

          {/* Hero visual — stacked cards */}
          <div className="hidden lg:block absolute right-12 top-1/2 -translate-y-1/2">
            <div className="relative">
              {/* CV preview card */}
              <div
                className="card p-6 w-[280px] rotate-2"
                style={{ boxShadow: "var(--shadow-lg)" }}
              >
                <div className="eyebrow mb-3">Your CV</div>
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                    style={{
                      background:
                        "linear-gradient(135deg, var(--green-600), var(--copper-500))",
                    }}
                  >
                    CM
                  </div>
                  <div>
                    <div className="font-semibold text-sm">Chanda Mwape</div>
                    <div className="text-xs" style={{ color: "var(--muted)" }}>
                      Senior Accountant
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {["Excel", "SAP", "IFRS", "Tax"].map((s) => (
                    <span key={s} className="tag tag-mono tag-green">
                      <Icon name="check" size={10} /> {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* WhatsApp notification card */}
              <div
                className="card p-4 w-[240px] absolute -bottom-12 -left-16 -rotate-3"
                style={{ boxShadow: "var(--shadow-lg)" }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    name="whatsapp"
                    size={16}
                    className="text-green-600"
                  />
                  <span className="text-xs font-medium" style={{ color: "var(--green-700)" }}>
                    WhatsApp
                  </span>
                </div>
                <p className="text-xs" style={{ color: "var(--ink-2)" }}>
                  New match: <strong>ZANACO Sr. Accountant</strong> — 92%
                  match score
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Stats Strip ─── */}
      <section
        className="py-10 md:py-14"
        style={{
          background: "var(--bg-2)",
          borderTop: "1px solid var(--line)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div
                className="font-display text-4xl md:text-5xl"
                style={{ color: "var(--green-700)" }}
              >
                <Counter to={stat.value} suffix={stat.suffix} />
              </div>
              <div
                className="mt-1 text-sm"
                style={{ color: "var(--muted)" }}
              >
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section className="py-16 md:py-24">
        <div className="max-w-[1280px] mx-auto px-6">
          <div className="text-center mb-12">
            <div className="eyebrow mb-3">How it works</div>
            <h2
              className="font-display"
              style={{
                fontSize: "clamp(32px, 4vw, 52px)",
                letterSpacing: "-0.02em",
              }}
            >
              Three steps to your{" "}
              <span className="italic" style={{ color: "var(--copper-500)" }}>
                next role
              </span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {howItWorks.map((step, i) => (
              <div key={step.title} className="card card-hover p-8">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
                  style={{
                    background: "var(--green-100)",
                    color: "var(--green-700)",
                  }}
                >
                  <Icon name={step.icon} size={22} />
                </div>
                <div
                  className="font-mono text-xs mb-2"
                  style={{ color: "var(--muted)" }}
                >
                  0{i + 1}
                </div>
                <h3
                  className="font-display text-2xl mb-3"
                  style={{ letterSpacing: "-0.01em" }}
                >
                  {step.title}
                </h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: "var(--muted)" }}
                >
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Score Breakdown Showcase ─── */}
      <section
        className="py-16 md:py-24"
        style={{ background: "var(--bg-2)" }}
      >
        <div className="max-w-[1280px] mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="eyebrow mb-3">Transparent matching</div>
              <h2
                className="font-display mb-4"
                style={{
                  fontSize: "clamp(32px, 4vw, 48px)",
                  letterSpacing: "-0.02em",
                }}
              >
                See exactly{" "}
                <span
                  className="italic"
                  style={{ color: "var(--copper-500)" }}
                >
                  why
                </span>{" "}
                each job fits
              </h2>
              <p
                className="text-base leading-relaxed mb-8"
                style={{ color: "var(--muted)" }}
              >
                No black boxes. Every match comes with a full breakdown —
                relevance, skills overlap, location fit — so you can see where
                you shine and where to grow.
              </p>
              <Link href="/auth" className="btn btn-primary">
                Try it free <Icon name="arrowRight" size={14} />
              </Link>
            </div>

            {/* Score card mockup */}
            <div className="card p-8" style={{ boxShadow: "var(--shadow-md)" }}>
              <div className="flex items-center gap-6 mb-6">
                <ScoreRing score={92} size={100} stroke={8} />
                <div>
                  <div className="font-display text-2xl">
                    Senior Accountant
                  </div>
                  <div
                    className="text-sm"
                    style={{ color: "var(--muted)" }}
                  >
                    ZANACO &middot; Lusaka
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                {[
                  { label: "Relevance", value: 95, tone: "green" },
                  { label: "Skills overlap", value: 88, tone: "copper" },
                  { label: "Local fit", value: 92, tone: "green" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between mb-1.5">
                      <span className="text-sm font-medium">{item.label}</span>
                      <span
                        className="font-mono text-xs"
                        style={{ color: "var(--muted)" }}
                      >
                        {item.value}/100
                      </span>
                    </div>
                    <div
                      className="h-1.5 rounded-full overflow-hidden"
                      style={{ background: "var(--bg)" }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{
                          width: `${item.value}%`,
                          background:
                            item.tone === "green"
                              ? "var(--green-500)"
                              : "var(--copper-500)",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Testimonials ─── */}
      <section className="py-16 md:py-24">
        <div className="max-w-[1280px] mx-auto px-6">
          <div className="text-center mb-12">
            <div className="eyebrow mb-3">What people say</div>
            <h2
              className="font-display"
              style={{
                fontSize: "clamp(32px, 4vw, 48px)",
                letterSpacing: "-0.02em",
              }}
            >
              Trusted by{" "}
              <span className="italic" style={{ color: "var(--copper-500)" }}>
                Zambian professionals
              </span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div key={t.name} className="card p-6">
                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Icon
                      key={s}
                      name="star"
                      size={14}
                      className="fill-current"
                      strokeWidth={0}
                    />
                  ))}
                </div>
                <p
                  className="text-sm leading-relaxed mb-6"
                  style={{ color: "var(--ink-2)" }}
                >
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                    style={{
                      background:
                        "linear-gradient(135deg, var(--green-600), var(--copper-500))",
                    }}
                  >
                    {t.name
                      .split(" ")
                      .map((w) => w[0])
                      .join("")}
                  </div>
                  <div>
                    <div className="text-sm font-medium">{t.name}</div>
                    <div
                      className="text-xs"
                      style={{ color: "var(--muted)" }}
                    >
                      {t.role}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Final CTA ─── */}
      <section className="py-16 md:py-24">
        <div className="max-w-[1280px] mx-auto px-6">
          <div
            className="relative overflow-hidden rounded-2xl p-10 md:p-16 text-center"
            style={{
              background:
                "linear-gradient(165deg, var(--green-800) 0%, var(--green-700) 60%, var(--copper-700) 130%)",
              color: "#faf7f2",
            }}
          >
            <div
              className="grain"
              style={{
                position: "absolute",
                inset: 0,
                opacity: 0.5,
              }}
            />
            <div
              className="absolute -top-10 -right-10 opacity-20 hidden md:block"
            >
              <ChevronMotif w={300} h={200} />
            </div>

            <div className="relative z-10">
              <div
                className="eyebrow mb-3"
                style={{ color: "rgba(255,255,255,0.6)" }}
              >
                Ready?
              </div>
              <h2
                className="font-display mb-4"
                style={{
                  fontSize: "clamp(32px, 5vw, 56px)",
                  letterSpacing: "-0.02em",
                }}
              >
                Your next career move{" "}
                <span className="italic" style={{ color: "var(--copper-300)" }}>
                  starts here
                </span>
              </h2>
              <p
                className="text-base md:text-lg mb-8 max-w-lg mx-auto"
                style={{ opacity: 0.85 }}
              >
                Join thousands of Zambian professionals using AI to land better
                jobs, faster.
              </p>
              <Link
                href="/auth"
                className="btn btn-lg"
                style={{
                  background: "#faf7f2",
                  color: "var(--green-800)",
                  fontWeight: 600,
                }}
              >
                Get Started Free <Icon name="arrowRight" size={16} />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
