"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Check, MessageCircle } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TIER_INFO } from "@/lib/constants";
import { cn } from "@/lib/utils";

const features = [
  { t: "AI-Powered Matching", d: "Vector + skill matching tuned for the Zambian market." },
  { t: "WhatsApp delivery", d: "Daily nudges and matches straight to the app you already use." },
  { t: "Cover letter help", d: "Tailored drafts you can send with every application (paid tiers)." },
  { t: "Mobile money", d: "MTN & Airtel Money. Start free, upgrade when you are ready." },
  { t: "Smart CV parsing", d: "Upload PDF or DOCX — we surface skills to match against jobs." },
  { t: "Daily job alerts", d: "New listings and deadlines so you never miss a close date." },
];

const steps = [
  {
    t: "Upload your CV",
    d: "PDF, DOC, or photo. We extract skills, experience, location in seconds.",
  },
  {
    t: "AI scores every job",
    d: "Hybrid match: 60% semantic similarity + 30% skills overlap + 10% bonus signals.",
  },
  {
    t: "Multi-channel apply",
    d: "Email, WhatsApp, phone, or website — whichever the employer accepts.",
  },
  {
    t: "Daily WhatsApp digest",
    d: "Top 3 matches at 07:00. Reply YES to apply. No spam, no scrolling.",
  },
];

const scoreBars = [
  { label: "Semantic similarity", pct: 60, bar: "bg-emerald-500" },
  { label: "Skills overlap", pct: 30, bar: "bg-amber-500" },
  { label: "Bonus signals", pct: 10, bar: "bg-slate-400" },
] as const;

function getStepMotion(reduce: boolean) {
  if (reduce) {
    return {};
  }
  return { initial: { y: 12, opacity: 0 }, whileInView: { y: 0, opacity: 1, transition: { duration: 0.35 } } };
}

export function LandingPage() {
  const reduce = useReducedMotion() ?? false;

  return (
    <div>
      <section
        className="relative overflow-hidden py-10 sm:py-16 bg-slate-950"
        aria-label="Intro"
      >
        <div className="grid gap-10 md:grid-cols-2 md:items-center md:gap-12">
          <div>
            <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-50">
              The job match built{" "}
              <span className="bg-gradient-to-r from-emerald-400 to-green-500 bg-clip-text text-transparent">
                in Zambia
              </span>{" "}
              for you
            </h1>
            <p className="mt-4 text-base sm:text-lg text-slate-400 max-w-xl">
              ZedApply runs hybrid AI matching, then brings what matters to WhatsApp — the channel most
              of us use every day.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                className={cn(
                  buttonVariants({ variant: "default" }),
                  "min-h-11 h-10 px-6 text-base w-full sm:w-auto inline-flex items-center justify-center rounded-lg"
                )}
                href="/auth"
              >
                Get started free
              </Link>
              <a
                href="#how-it-works"
                className={cn(
                  buttonVariants({ variant: "outline" }),
                  "min-h-11 h-10 justify-center text-center text-base w-full sm:w-auto border-slate-700 text-slate-200 hover:bg-slate-800"
                )}
              >
                See how it works
              </a>
            </div>
            <p className="mt-4 flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-1 text-xs sm:text-sm text-slate-500">
              <span className="inline-flex items-center gap-1">
                <Check className="h-3.5 w-3.5 text-emerald-500" aria-hidden />
                No credit card for Free
              </span>
              <span className="hidden sm:inline" aria-hidden>
                &bull;
              </span>
              <span>Results via WhatsApp</span>
            </p>
          </div>
          <div className="flex justify-center md:justify-end">
            <div
              className="animate-float w-full max-w-[340px] rounded-2xl border border-white/10 bg-[#0b141a] p-4 sm:p-5 shadow-2xl shadow-black/40 ring-1 ring-white/5"
              role="img"
              aria-label="WhatsApp digest preview"
            >
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#25D366] text-white">
                  <MessageCircle className="h-4 w-4" aria-hidden />
                </div>
                <span className="text-xs text-[#8696a0]">ZedApply · 07:00</span>
              </div>
              <p className="text-[15px] font-medium text-[#e9edef]">
                Good morning Chanda! 3 new matches:
              </p>
              <ul className="mt-4 flex flex-col gap-2">
                <li className="rounded-xl bg-[#1f2c34] px-3 py-2.5 text-[13px] text-[#d1d7db]">
                  <span className="font-semibold text-[#e9edef]">Senior Accountant</span>
                  <span className="text-[#8696a0]"> · ZANACO</span>
                  <span className="text-[#25D366]"> (92%)</span>
                </li>
                <li className="rounded-xl bg-[#1f2c34] px-3 py-2.5 text-[13px] text-[#d1d7db]">
                  <span className="font-semibold text-[#e9edef]">Frontend Engineer</span>
                  <span className="text-[#8696a0]"> · MTN</span>
                  <span className="text-[#25D366]"> (88%)</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="py-12 sm:py-24 bg-slate-950 border-y border-slate-800"
        aria-labelledby="how-h"
      >
        <h2
          id="how-h"
          className="font-serif text-2xl sm:text-4xl font-bold text-center text-slate-50"
        >
          Four steps. One coffee.
        </h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 sm:gap-5 max-w-6xl mx-auto px-4">
          {steps.map((s) => (
            <motion.div
              key={s.t}
              viewport={{ once: true, margin: "-5%" }}
              className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 h-full"
              {...getStepMotion(reduce)}
            >
              <h3 className="font-semibold text-slate-50 text-lg">{s.t}</h3>
              <p className="text-sm text-slate-400 mt-2 leading-relaxed">{s.d}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="py-12 sm:py-20" aria-labelledby="scoring-h">
        <div className="max-w-6xl mx-auto px-4 grid gap-10 lg:grid-cols-2 items-center">
          <div>
            <h2 id="scoring-h" className="text-2xl sm:text-3xl font-bold text-foreground">
              Every match shows{" "}
              <span className="italic text-emerald-600 dark:text-emerald-400">its math</span>.
            </h2>
            <p className="mt-3 text-muted-foreground text-base leading-relaxed">
              No black box. Every score breaks down into three components, and the AI writes a
              one-paragraph explanation in plain English — like a recruiter would.
            </p>
          </div>
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base">Senior Accountant · ZANACO</CardTitle>
              <CardDescription>Score breakdown</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5">
              {scoreBars.map(({ label, pct, bar }) => (
                <div key={label}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono text-xs text-muted-foreground">{pct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div className={cn("h-full rounded-full", bar)} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              ))}
              <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4 dark:bg-muted/20">
                <p className="text-xs font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-400 mb-1.5">
                  AI explanation
                </p>
                <p className="text-sm leading-relaxed text-foreground dark:text-gray-200 m-0">
                  Strong overlap on IFRS reporting and Excel modeling. Lusaka location matches your
                  profile. One missing skill: SAP — minor for this role.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section
        id="features"
        className="py-12 sm:py-20"
        aria-labelledby="feat-h"
      >
        <h2 id="feat-h" className="text-2xl sm:text-3xl font-bold text-foreground text-center">
          What you get
        </h2>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto px-4">
          {features.map((f) => (
            <Card key={f.t} className="border border-border/80">
              <CardHeader>
                <CardTitle className="text-base">{f.t}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-sm leading-relaxed">{f.d}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="py-12 sm:py-20" aria-labelledby="price-h">
        <h2 id="price-h" className="text-2xl sm:text-3xl font-bold text-center text-foreground">
          Plan preview
        </h2>
        <div className="mt-8 grid sm:grid-cols-3 gap-4 max-w-5xl mx-auto px-4">
          {(["free", "starter", "professional"] as const).map((key) => {
            const t = TIER_INFO[key];
            return (
              <Card key={key} className={cn("border-2", key === "starter" && "ring-2 ring-primary")}>
                <CardHeader>
                  <CardTitle>{t.name}</CardTitle>
                  <CardDescription>{t.bemba}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-foreground">{t.priceLabel}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="py-12 px-4" aria-label="Call to action">
        <div className="max-w-4xl mx-auto rounded-2xl overflow-hidden p-8 sm:p-10 text-center text-white bg-gradient-to-r from-emerald-600 to-green-500">
          <MessageCircle className="inline-block h-8 w-8 opacity-90 mb-3" strokeWidth={1.75} aria-hidden />
          <h2 className="text-xl sm:text-2xl font-bold">
            Your next role is already in our database.
          </h2>
          <div className="mt-6">
            <Link
              href="/auth"
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-white px-8 text-base font-medium text-emerald-800 shadow-sm hover:bg-white/90"
            >
              Begin with WhatsApp
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
