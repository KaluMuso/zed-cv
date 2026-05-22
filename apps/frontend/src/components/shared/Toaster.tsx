"use client";

import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      position="top-center"
      duration={5000}
      toastOptions={{
        classNames: {
          toast:
            "rounded-md border bg-surface-elevated text-ink shadow-card dark:bg-surface-dark-elevated dark:text-ink-dark",
          success: "border-success-500/30 [&_[data-icon]]:text-success-500",
          error: "border-danger-500/30 [&_[data-icon]]:text-danger-500",
          info: "border-primary-500/30 [&_[data-icon]]:text-primary-500",
        },
      }}
    />
  );
}
