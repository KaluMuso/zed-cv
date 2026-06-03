"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { ScoreBreakdownMockup } from "@/components/marketing/ScoreBreakdownMockup";
import {
  MATCH_WEIGHT_BULLETS,
  MATCH_WEIGHT_COMPONENT_COUNT,
} from "@/lib/matching-weights-copy";

const bullets = MATCH_WEIGHT_BULLETS;

const viewport = { once: true, margin: "-80px" } as const;

/** Semantic text classes for WCAG AA contrast on bg-background / bg-bg-2 in both themes. */
export const SCORE_MATH_SECTION_TEXT = {
  eyebrow: "font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground",
  heading: "font-display mt-2 text-display-md text-foreground md:text-display-lg",
  lead: "mt-5 max-w-[520px] text-base leading-relaxed text-muted-foreground",
  bulletTitle: "font-semibold text-foreground",
  bulletBody: "text-sm text-muted-foreground",
} as const;

export function ScoreMathSection() {
  const reduce = useReducedMotion() ?? false;

  return (
    <section className="border-y border-border bg-bg-2">
      <div className="mx-auto max-w-[1280px] px-5 py-16 sm:px-6 sm:py-20 md:py-24">
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 12 }}
            whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
            viewport={viewport}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <p className={SCORE_MATH_SECTION_TEXT.eyebrow}>
              § 02 / Transparent scoring
            </p>
            <h2 className={SCORE_MATH_SECTION_TEXT.heading}>
              Every match shows its math.
            </h2>
            <p className={SCORE_MATH_SECTION_TEXT.lead}>
              No black box. Every score breaks down into {MATCH_WEIGHT_COMPONENT_COUNT}{" "}
              components, and the AI writes a one-paragraph explanation in plain English —
              like a recruiter would.
            </p>
            <ul className="mt-7 flex list-none flex-col gap-3.5 p-0">
              {bullets.map(({ title, body }) => (
                <li key={title} className="flex items-start gap-3.5">
                  <div
                    className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700 dark:bg-green-100/20 dark:text-green-400"
                    aria-hidden
                  >
                    <Check className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className={SCORE_MATH_SECTION_TEXT.bulletTitle}>{title}</div>
                    <div className={SCORE_MATH_SECTION_TEXT.bulletBody}>{body}</div>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 16 }}
            whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
            viewport={viewport}
            transition={{ duration: 0.55, ease: "easeOut", delay: 0.1 }}
          >
            <ScoreBreakdownMockup />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
