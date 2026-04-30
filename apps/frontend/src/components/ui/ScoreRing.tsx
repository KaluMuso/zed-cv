"use client";

import { useEffect, useState, useRef } from "react";

interface ScoreRingProps {
  score: number;
  size?: number;
  stroke?: number;
}

function getColor(score: number): string {
  if (score >= 85) return "var(--green-500)";
  if (score >= 70) return "var(--copper-500)";
  return "var(--orange-500)";
}

export function ScoreRing({ score, size = 80, stroke = 6 }: ScoreRingProps) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const target = circumference - (score / 100) * circumference;
    const timer = setTimeout(() => setOffset(target), 100);
    return () => clearTimeout(timer);
  }, [score, circumference]);

  const color = getColor(score);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        ref={ref}
        width={size}
        height={size}
        className="-rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="score-ring-track"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.2,0.7,0.2,1)" }}
        />
      </svg>
      <span
        className="absolute font-display font-bold"
        style={{
          fontSize: size * 0.32,
          color,
        }}
      >
        {Math.round(score)}
      </span>
    </div>
  );
}
