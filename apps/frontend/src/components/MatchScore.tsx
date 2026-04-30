"use client";

import { ScoreRing } from "@/components/ui/ScoreRing";

interface ScoreBreakdown {
  vector: number;
  skill: number;
  bonus: number;
}

interface MatchScoreProps {
  score: number;
  breakdown: ScoreBreakdown;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: { ring: 64, stroke: 5 },
  md: { ring: 80, stroke: 6 },
  lg: { ring: 108, stroke: 9 },
};

export function MatchScore({ score, breakdown, size = "md" }: MatchScoreProps) {
  const { ring, stroke } = sizes[size];

  return (
    <div className="relative">
      <ScoreRing score={score} size={ring} stroke={stroke} />
      <div
        className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider"
        style={{
          background:
            score >= 85
              ? "var(--green-700)"
              : score >= 70
              ? "var(--copper-500)"
              : "var(--orange-500)",
          color: "#faf7f2",
          whiteSpace: "nowrap",
        }}
      >
        {score >= 85 ? "Top match" : score >= 70 ? "Good fit" : "Stretch"}
      </div>
    </div>
  );
}
