"use client";

interface LogoProps {
  size?: number;
}

export function Logo({ size = 28 }: LogoProps) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="flex items-center justify-center rounded-lg font-display text-white font-bold"
        style={{
          width: size,
          height: size,
          fontSize: size * 0.55,
          background: "var(--green-700)",
        }}
      >
        Z
      </div>
      <span
        className="font-display tracking-tight"
        style={{ fontSize: size * 0.75, letterSpacing: "-0.02em" }}
      >
        Zed<span style={{ color: "var(--copper-500)" }}>Apply</span>
      </span>
    </div>
  );
}
