"use client";

import type { PropsWithChildren } from "react";
import type { RouteTransitionVariant } from "@/lib/mobile-transitions";
import { cn } from "@/lib/utils";

const VARIANT_CLASS: Record<RouteTransitionVariant, string> = {
  fade: "page-enter",
  "tab-left": "page-enter-tab-left",
  "tab-right": "page-enter-tab-right",
};

/** CSS-only route enter — avoids framer-motion bundle + layout thrash. */
export function PageTransition({
  children,
  variant = "fade",
}: PropsWithChildren<{ variant?: RouteTransitionVariant }>) {
  return <div className={cn(VARIANT_CLASS[variant])}>{children}</div>;
}
