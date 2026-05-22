"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

interface FinalCtaSectionProps {
  primaryHref: string;
}

const viewport = { once: true, margin: "-80px" } as const;

export function FinalCtaSection({ primaryHref }: FinalCtaSectionProps) {
  const reduce = useReducedMotion() ?? false;

  return (
    <section className="mx-auto max-w-[1280px] px-5 py-16 sm:px-6 sm:py-20 md:py-24">
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 12 }}
        whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
        viewport={viewport}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="grain relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-600 to-green-500 px-6 py-10 text-white sm:rounded-3xl sm:px-10 sm:py-14"
      >
        <div
          className="pointer-events-none absolute hidden md:block"
          style={{ right: -40, top: -40, opacity: 0.18 }}
          aria-hidden
        >
          <ChevronMotif w={420} h={400} />
        </div>
        <div className="relative">
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-white/70">
            § Stop scrolling Facebook groups
          </p>
          <h2 className="font-display mt-3 max-w-[800px] text-display-md sm:text-[clamp(28px,5vw,56px)] sm:leading-[1.08]">
            Your next role is already{" "}
            <span className="italic text-[#F5E6D3]">in our database.</span>
          </h2>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href={primaryHref}
              className={cn(
                "btn btn-lg bg-white font-semibold text-emerald-800 transition-transform hover:scale-[1.02] hover:bg-white/90"
              )}
            >
              Start free <Icon name="arrowRight" size={16} />
            </Link>
            <Link
              href="/pricing"
              className={cn(
                "btn btn-lg border border-white/30 bg-transparent text-white transition-transform hover:scale-[1.02] hover:bg-white/10"
              )}
            >
              See pricing
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
