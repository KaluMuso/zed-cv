import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const pillVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default:
          "border-border bg-surface text-ink-muted dark:border-border-dark dark:bg-surface-dark-elevated dark:text-ink-dark-muted",
        green:
          "border-transparent bg-primary-100 text-primary-700 dark:bg-primary-500/15 dark:text-primary-100",
        copper:
          "border-transparent bg-accent-100 text-accent-600 dark:bg-accent-500/15 dark:text-accent-100",
        orange:
          "border-transparent bg-warning-500/15 text-warning-500 dark:bg-warning-500/20",
        muted:
          "border-transparent bg-ink-muted/10 text-ink-muted dark:bg-ink-dark-muted/20 dark:text-ink-dark-muted",
        success:
          "border-transparent bg-success-500/10 text-success-500",
        warning:
          "border-transparent bg-warning-500/10 text-warning-500",
        danger:
          "border-transparent bg-danger-500/10 text-danger-500",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2 py-0.5 text-xs",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

function Pill({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof pillVariants>) {
  return (
    <span className={cn(pillVariants({ variant, size, className }))} {...props} />
  );
}

export { Pill, pillVariants };
