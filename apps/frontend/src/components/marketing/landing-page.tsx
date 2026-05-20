"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Check, FileUp, MessageCircle, Sparkles, Smartphone, Wallet, Bell, PenLine, Search, ShieldCheck, Languages, Wifi } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TIER_INFO } from "@/lib/constants";
import { cn } from "@/lib/utils";

const features = [
  { icon: Search, t: "AI-Powered Matching", d: "Vector + skill matching tuned for the Zambian market." },
  { icon: MessageCircle, t: "WhatsApp delivery", d: "Daily nudges and matches straight to the app you already use." },
  { icon: PenLine, t: "Cover letter help", d: "Tailored drafts you can send with every application (paid tiers)." },
  { icon: Wallet, t: "Mobile money", d: "MTN & Airtel Money. Start free, upgrade when you are ready." },
  { icon: FileUp, t: "Smart CV parsing", d: "Upload PDF or DOCX — we surface skills to match against jobs." },
  { icon: Bell, t: "Daily job alerts", d: "New listings and deadlines so you never miss a close date." },
];

const steps = [
  { icon: FileUp, t: "Upload your CV", d: "PDF, Word, or a clear image — we extract your skills in seconds." },
  { icon: Sparkles, t: "Run AI matching", d: "We score you against open roles: relevance, skills, and small bonuses." },
  { icon: Smartphone, t: "Get results on WhatsApp", d: "Shortlist-style updates and reminders in chat." },
];

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
        className="relative overflow-hidden py-10 sm:py-16"
        style={{
          backgroundImage: [
            "radial-gradient(60% 80% at 80% 0%, color-mix(in srgb, var(--primary) 20%, transparent), transparent 70%)",
            "radial-gradient(50% 60% at 10% 20%, color-mix(in srgb, var(--primary) 8%, transparent), transparent 60%)",
            "repeating-linear-gradient(135deg, color-mix(in srgb, var(--foreground) 2%, transparent) 0, transparent 1px, transparent 12px, color-mix(in srgb, var(--foreground) 2%, transparent) 12px, color-mix(in srgb, var(--foreground) 2%, transparent) 13px)",
          ].join(", "),
        }}
        aria-label="Intro"
      >
        <div className="grid gap-10 md:grid-cols-2 md:items-center md:gap-12">
          <div>
            <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-foreground">
              The job match built{" "}
              <span
                className="bg-clip-text text-transparent"
                style={{
                  backgroundImage: "linear-gradient(100deg, var(--primary) 0%, #15803d 55%, var(--primary) 100%)",
                }}
              >
                in Zambia
              </span>{" "}
              for you
            </h1>
            <p className="mt-4 text-base sm:text-lg text-muted-foreground max-w-xl">
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
                  "min-h-11 h-10 justify-center text-center text-base w-full sm:w-auto"
                )}
              >
                See how it works
              </a>
            </div>
            <p className="mt-4 flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-1 text-xs sm:text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Check className="h-3.5 w-3.5 text-primary" aria-hidden />
                No credit card for Free
              </span>
              <span className="hidden sm:inline" aria-hidden>
                &bull;
              </span>
              <span>Results via WhatsApp</span>
              <span className="hidden sm:inline" aria-hidden>
                &bull;
              </span>
              <span>Change plan anytime</span>
            </p>
          </div>
          <div className="flex justify-center md:justify-end">
            <div className="relative w-56 sm:w-64 aspect-[9/19]">
              <div
                className="absolute inset-0 rounded-[2rem] border-4 border-muted bg-card shadow-2xl ring-1 ring-border/60"
                role="img"
                aria-label="ZedApply app on a phone (illustration)"
              >
                <div className="h-6 rounded-t-[1.5rem] bg-muted flex items-center justify-center text-[0.6rem] text-muted-foreground">
                  Your matches
                </div>
                <div className="p-3 space-y-2">
                  <div className="h-2 w-1/2 rounded bg-primary/20" />
                  <div className="h-16 rounded-lg bg-primary/5 border border-primary/20" />
                  <div className="h-2 w-3/4 rounded bg-muted" />
                </div>
                <p className="px-3 pb-3 text-[0.6rem] text-center text-muted-foreground">
                  Illustration
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="py-12 sm:py-24"
        aria-labelledby="how-h"
      >
        <h2 id="how-h" className="text-2xl sm:text-3xl font-bold text-center text-foreground">
          How it works
        </h2>
        <p className="text-center text-muted-foreground text-base mt-2 max-w-2xl mx-auto">
          Three short steps from CV to the jobs that line up with your story.
        </p>
        <div className="mt-10 grid gap-8 sm:grid-cols-3 sm:gap-6">
          {steps.map((s) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.t}
                viewport={{ once: true, margin: "-5%" }}
                {...getStepMotion(reduce)}
              >
                <div className="text-center h-full p-4 rounded-2xl border border-border/80 bg-card/50">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mb-3" aria-hidden>
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="font-semibold text-foreground text-lg">{s.t}</h3>
                  <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{s.d}</p>
                </div>
              </motion.div>
            );
          })}
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
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <Card
                key={f.t}
                className="transition duration-200 hover:shadow-md hover:-translate-y-0.5 border border-border/80"
              >
                <CardHeader>
                  <Icon className="h-8 w-8 text-primary" aria-hidden />
                  <CardTitle className="text-base">{f.t}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                    {f.d}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="py-12 sm:py-20" id="about" aria-labelledby="social-h">
        <h2 id="social-h" className="sr-only">
          Built for Zambia
        </h2>
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h3 className="text-xl sm:text-2xl font-bold text-foreground">Built for real people on real phones</h3>
          <p className="text-muted-foreground text-base mt-2">
            3G-friendly screens, big tap targets, and the channels that already work in Zambia. We are early —
            here is what you can count on from day one.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
          {[
            {
              icon: ShieldCheck,
              t: "WhatsApp OTP sign-in",
              d: "No passwords to forget, no email loops. Verify with the number you already use.",
            },
            {
              icon: Wallet,
              t: "MTN & Airtel Money",
              d: "Pay in kwacha when you upgrade. The Free tier stays K0 forever — no card needed.",
            },
            {
              icon: Languages,
              t: "English & Bemba",
              d: "Switch your WhatsApp messages to icibemba in Settings. More languages on the way.",
            },
          ].map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.t}
                className="rounded-2xl border border-border/80 bg-card/50 p-5 text-center sm:text-left"
              >
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary mb-3" aria-hidden>
                  <Icon className="h-5 w-5" />
                </div>
                <h4 className="font-semibold text-foreground">{p.t}</h4>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{p.d}</p>
              </div>
            );
          })}
        </div>
        <p className="text-center text-xs text-muted-foreground mt-6 inline-flex items-center gap-1.5 w-full justify-center">
          <Wifi className="h-3.5 w-3.5" aria-hidden />
          Tested on 3G. We will publish real usage numbers once the platform is live.
        </p>
      </section>

      <section className="py-12 sm:py-20" aria-labelledby="price-h">
        <h2 id="price-h" className="text-2xl sm:text-3xl font-bold text-center text-foreground">
          Plan preview
        </h2>
        <p className="text-center text-muted-foreground text-base mt-1 mb-8 max-w-2xl mx-auto">
          Bemba names. Honest ZMW pricing. Full comparison on the pricing page.
        </p>
        <div className="grid sm:grid-cols-3 gap-4 max-w-5xl mx-auto">
          {(["free", "starter", "professional"] as const).map((key) => {
            const t = TIER_INFO[key];
            return (
              <Card
                key={key}
                className={cn("border-2", key === "starter" && "ring-2 ring-primary shadow-lg")}
              >
                <CardHeader>
                  {key === "starter" && <span className="text-xs font-medium text-primary">Most popular</span>}
                  <CardTitle>{t.name}</CardTitle>
                  <CardDescription>{t.bemba}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-foreground">
                    {t.priceLabel}{" "}
                    <span className="text-sm font-normal text-muted-foreground">
                      {key === "free" ? "forever" : "/ month"}
                    </span>
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
        <div className="text-center mt-8">
          <Link
            className={cn(
              buttonVariants({ variant: "link" }),
              "text-primary text-base min-h-11 inline-flex"
            )}
            href="/pricing"
          >
            View full pricing &rarr;
          </Link>
        </div>
      </section>

      <section
        className="py-12"
        aria-label="Call to action"
      >
        <div
          className="rounded-2xl overflow-hidden p-8 sm:p-10 text-center text-primary-foreground"
          style={{ background: "linear-gradient(120deg, #14532d 0%, #166534 50%, #15803d 100%)" }}
        >
          <MessageCircle
            className="inline-block h-8 w-8 sm:h-9 sm:w-9 opacity-90 mb-3"
            strokeWidth={1.75}
            aria-hidden
          />
          <h2 className="text-xl sm:text-2xl font-bold">Start matching in about a minute</h2>
          <p className="text-sm sm:text-base opacity-90 mt-2 max-w-lg mx-auto">
            Sign in with WhatsApp OTP, upload your CV, and see how you score. No long forms, no email loops.
          </p>
          <div className="mt-6">
            <Link
              href="/auth"
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary-foreground px-8 text-base font-medium text-primary shadow-sm transition hover:bg-primary-foreground/90"
            >
              Begin with WhatsApp
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
