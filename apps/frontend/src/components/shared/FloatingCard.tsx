import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Props = {
  delay?: boolean;
  angle?: number;
  children: ReactNode;
};

export function FloatingCard({ delay = false, angle = -2, children }: Props) {
  return (
    <div
      className={cn(
        "transform-gpu will-change-transform",
        delay ? "animate-float-delayed" : "animate-float"
      )}
      style={{ rotate: `${angle}deg` }}
    >
      {children}
    </div>
  );
}
