"use client";

const SIZE = 56;
const STROKE = 4;
const R = (SIZE - STROKE) / 2;
const CIRC = 2 * Math.PI * R;

type Phase = "countdown" | "working";

interface CountdownRingProps {
  phase: Phase;
  /** Total countdown seconds (from API). */
  total: number;
  /** Seconds remaining in countdown phase (ceil). */
  secondsLeft: number;
}

/**
 * SVG ring: full arc at start of countdown, drains to empty at 0.
 * In `working` phase, shows a spinning ring (Tailwind animate-spin).
 */
export function CountdownRing({ phase, total, secondsLeft }: CountdownRingProps) {
  const progress =
    phase === "countdown" && total > 0
      ? Math.min(1, Math.max(0, secondsLeft / total))
      : 0;
  const offset = CIRC * (1 - progress);

  return (
    <div
      className={phase === "working" ? "inline-flex animate-spin" : "inline-flex"}
      style={{ width: SIZE, height: SIZE }}
      aria-hidden
    >
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          fill="none"
          stroke="var(--line-2)"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          fill="none"
          stroke="var(--green-500)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRC}
          strokeDashoffset={phase === "working" ? CIRC * 0.2 : offset}
          style={{
            transform: "rotate(-90deg)",
            transformOrigin: "50% 50%",
            transition:
              phase === "countdown"
                ? "stroke-dashoffset 0.95s linear"
                : "stroke-dashoffset 0.6s ease",
          }}
        />
      </svg>
    </div>
  );
}
