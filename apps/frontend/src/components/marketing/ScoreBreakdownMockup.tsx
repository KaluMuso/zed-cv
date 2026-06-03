"use client";

import { motion, useReducedMotion } from "framer-motion";
const bars = [
  { label: "Semantic similarity", value: 95 },
  { label: "Skills overlap", value: 88 },
  { label: "Experience fit", value: 82 },
  { label: "Location", value: 90 },
  { label: "Recency", value: 78 },
] as const;

const viewport = { once: true, margin: "-80px" } as const;

function scoreColor(score: number): string {
  if (score >= 80) return "var(--green-500)";
  if (score >= 60) return "var(--copper-500)";
  return "var(--orange-500)";
}

function AnimatedScoreRing({ score, size = 72 }: { score: number; size?: number }) {
  const reduce = useReducedMotion() ?? false;
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const color = scoreColor(score);

  return (
    <div className="relative inline-flex shrink-0 items-center justify-center">
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="stroke-bg-2 dark:stroke-muted/30"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={reduce ? { strokeDashoffset: circumference - (score / 100) * circumference } : { strokeDashoffset: circumference }}
          whileInView={
            reduce
              ? undefined
              : { strokeDashoffset: circumference - (score / 100) * circumference }
          }
          viewport={viewport}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </svg>
      <span
        className="absolute font-display text-lg font-bold tabular-nums"
        style={{ color }}
      >
        {score}
      </span>
    </div>
  );
}

function ScoreBar({
  label,
  value,
  index,
}: {
  label: string;
  value: number;
  index: number;
}) {
  const reduce = useReducedMotion() ?? false;

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[13px] text-muted-foreground">
          {label}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {value}/100
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-2 dark:bg-muted/30">
        <motion.div
          className="h-full rounded-full bg-brand"
          initial={reduce ? { width: `${value}%` } : { width: "0%" }}
          whileInView={reduce ? undefined : { width: `${value}%` }}
          viewport={viewport}
          transition={{ duration: 0.6, ease: "easeOut", delay: index * 0.08 }}
        />
      </div>
    </div>
  );
}

export function ScoreBreakdownMockup() {
  return (
    <div
      className="rounded-md border border-border bg-card p-6 shadow-md sm:p-8"
      style={{ boxShadow: "var(--shadow-md)" }}
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-display text-[22px] leading-tight text-foreground">
            Senior Accountant
          </div>
          <div className="mt-0.5 text-[13px] text-muted-foreground">
            ZANACO · Lusaka
          </div>
        </div>
        <AnimatedScoreRing score={92} />
      </div>

      <div className="flex flex-col gap-3.5">
        {bars.map((bar, i) => (
          <ScoreBar key={bar.label} label={bar.label} value={bar.value} index={i} />
        ))}
      </div>

      <div className="mt-5 rounded-md border border-border bg-muted/40 p-4 text-foreground">
        <p className="mb-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
          Explanation
        </p>
        <p className="m-0 text-[13px] leading-relaxed">
          Your CV shows strong overlap with Excel and IFRS. Your audit and
          reconciliation experience matches the existing Senior Audit &amp;
          Madison experience window the hiring manager… Lusaka matches your
          profile. Closing 92% — refreshed 2h ago.
        </p>
      </div>
    </div>
  );
}
