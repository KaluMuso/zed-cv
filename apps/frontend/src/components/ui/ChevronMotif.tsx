"use client";

interface ChevronMotifProps {
  w?: number;
  h?: number;
}

export function ChevronMotif({ w = 300, h = 200 }: ChevronMotifProps) {
  const rows = Math.ceil(h / 32);
  const cols = Math.ceil(w / 32);
  const chevrons: JSX.Element[] = [];

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = c * 32;
      const y = r * 32;
      const fill = (r + c) % 2 === 0 ? "var(--green-600)" : "var(--copper-500)";
      chevrons.push(
        <path
          key={`${r}-${c}`}
          d={`M${x},${y + 16} L${x + 16},${y} L${x + 32},${y + 16}`}
          fill="none"
          stroke={fill}
          strokeWidth={2}
          opacity={0.4}
        />
      );
    }
  }

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      style={{ overflow: "visible" }}
    >
      {chevrons}
    </svg>
  );
}
