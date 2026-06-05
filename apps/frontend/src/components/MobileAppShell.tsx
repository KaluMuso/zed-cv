"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { showMobileAppShell } from "@/lib/mobile-nav";

/**
 * Toggles document-level classes for authenticated mobile app routes
 * (native scroll, tap highlight, compact chrome).
 */
export function MobileAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated } = useAuth();
  const active = showMobileAppShell(pathname, isAuthenticated);

  useEffect(() => {
    document.documentElement.classList.toggle("mobile-app-shell", active);
    return () => {
      document.documentElement.classList.remove("mobile-app-shell");
    };
  }, [active]);

  return children;
}
