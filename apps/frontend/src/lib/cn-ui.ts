/**
 * Design-system helpers — prefer these over legacy `.btn` / `.card` classes in new code.
 */
import { type VariantProps } from "class-variance-authority";

import { buttonVariants } from "@/components/ui/button";
import { badgeVariants } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type ButtonVariant = NonNullable<VariantProps<typeof buttonVariants>["variant"]>;
type ButtonSize = NonNullable<VariantProps<typeof buttonVariants>["size"]>;

/** className for `<Link>` or `<button>` matching shadcn Button */
export function btnClass(
  variant: ButtonVariant | "accent" = "primary",
  size: ButtonSize = "default",
  className?: string,
) {
  return cn(buttonVariants({ variant, size }), className);
}

/** Pill chips (replaces `.tag` / `.tag-green` etc.) */
export function tagClass(
  tone: "default" | "green" | "copper" | "orange" | "mono" = "default",
  className?: string,
) {
  const toneClass =
    tone === "green"
      ? "border-transparent bg-primary/10 text-primary dark:bg-primary/20"
      : tone === "copper"
        ? "border-transparent bg-accent/15 text-accent-600 dark:text-accent"
        : tone === "orange"
          ? "border-transparent bg-warning/15 text-warning"
          : tone === "mono"
            ? "font-mono text-[11px] tracking-wide"
            : "";
  return cn(
    badgeVariants({ variant: "outline" }),
    "h-auto rounded-full px-2.5 py-0.5 text-xs font-medium",
    toneClass,
    className,
  );
}

/** Surface card (replaces bare `.card`) */
export const surfaceCardClass =
  "rounded-md border border-border bg-card text-foreground shadow-soft";
