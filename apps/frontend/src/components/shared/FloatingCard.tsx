import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Props = {
  /** First stagger (0.5s delay) */
  delay?: boolean;
  /** Third hero card stagger (1s delay) */
  delay2?: boolean;
  angle?: number;
  className?: string;
  children: ReactNode;
};

export function FloatingCard({
  delay = false,
  delay2 = false,
  angle = -2,
  className,
  children,
}: Props) {
  const animation = delay2
    ? "animate-float-delay-2"
    : delay
      ? "animate-float-delayed"
      : "animate-float";

  return (
    <div
      className={cn("transform-gpu will-change-transform", animation, className)}
      style={{ rotate: `${angle}deg` }}
    >
      {children}
    </div>
  );
}
