"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { PageTransition } from "@/components/shared/PageTransition";
import { useRouteTransitionDirection } from "@/hooks/useRouteTransitionDirection";

export function RouteTransitionShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const variant = useRouteTransitionDirection();
  const isAdmin = pathname?.startsWith("/admin") ?? false;

  if (isAdmin) {
    return <>{children}</>;
  }

  return (
    <div tabIndex={-1} className="outline-none min-h-[50vh]">
      <PageTransition key={pathname} variant={variant}>
        {children}
      </PageTransition>
    </div>
  );
}
