"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Bell, Send, Sparkles, Upload } from "lucide-react";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
const steps = [
  {
    n: "01",
    icon: Upload,
    title: "Upload your CV",
    description:
      "PDF, DOC, or photo. We extract skills, experience, location in seconds.",
  },
  {
    n: "02",
    icon: Sparkles,
    title: "AI scores every job",
    description:
      "Hybrid match: 60% semantic similarity + 30% skills overlap + 10% bonus signals.",
  },
  {
    n: "03",
    icon: Send,
    title: "Multi-channel apply",
    description:
      "Email, WhatsApp, phone, or website — whichever the employer accepts.",
  },
  {
    n: "04",
    icon: Bell,
    title: "Daily WhatsApp digest",
    description:
      "Top 3 matches at 07:00. Reply YES to apply. No spam, no scrolling.",
  },
] as const;

const staggerMs = [0, 80, 160, 240];

const viewport = { once: true, margin: "-80px" } as const;

export function FourStepsSection() {
  const reduce = useReducedMotion() ?? false;

  return (
    <section
      id="how-it-works"
      className="relative overflow-hidden border-y border-slate-800/80 bg-slate-950"
    >
      <div
        className="pointer-events-none absolute right-4 top-6 opacity-[0.12] sm:right-8"
        aria-hidden
      >
        <ChevronMotif w={160} h={120} />
      </div>

      <div className="relative mx-auto max-w-[1280px] px-5 py-16 sm:px-6 sm:py-20 md:py-24">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 12 }}
          whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
          viewport={viewport}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="max-w-3xl"
        >
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500">
            § 01 / How it works
          </p>
          <h2 className="font-display mt-3 text-display-md text-slate-50 md:text-display-lg">
            Four steps.{" "}
            <span className="italic text-[#D97706]">One coffee.</span>
          </h2>
        </motion.div>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-12 md:grid-cols-4 sm:gap-5">
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <motion.article
                key={step.n}
                initial={reduce ? false : { opacity: 0, y: 16 }}
                whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
                viewport={viewport}
                transition={{
                  duration: 0.55,
                  ease: "easeOut",
                  delay: reduce ? 0 : staggerMs[i] / 1000,
                }}
                className="rounded-md border border-slate-800 bg-slate-900/90 p-6 sm:p-7"
              >
                <div className="flex items-start justify-between">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-md bg-emerald-500/15 text-emerald-400">
                    <Icon className="h-5 w-5" aria-hidden />
                  </div>
                  <span className="font-mono text-xs text-slate-500">
                    {step.n}
                  </span>
                </div>
                <h3 className="font-display mt-5 text-xl text-slate-50 sm:mt-6">
                  {step.title}
                </h3>
                <p className="m-0 mt-2 text-sm leading-relaxed text-slate-400">
                  {step.description}
                </p>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
