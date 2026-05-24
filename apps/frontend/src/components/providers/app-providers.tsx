"use client";

import { ThemeProvider } from "./theme-provider";
import { Toaster } from "@/components/shared/Toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RegisterServiceWorker } from "./register-service-worker";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <TooltipProvider delay={200}>
        {children}
        <Toaster />
        <RegisterServiceWorker />
      </TooltipProvider>
    </ThemeProvider>
  );
}
