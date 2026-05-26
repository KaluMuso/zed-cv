"use client";

import type { PropsWithChildren } from "react";

/** CSS-only route enter — avoids framer-motion bundle + layout thrash. */
export function PageTransition({ children }: PropsWithChildren) {
  return <div className="page-enter">{children}</div>;
}
