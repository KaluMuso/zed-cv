import * as React from "react";
import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button relative inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-transparent font-medium whitespace-nowrap transition-all duration-base ease-out-soft outline-none select-none active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-primary-500/30 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary-500 text-primary-foreground hover:bg-primary-600 shadow-soft",
        primary:
          "bg-primary-500 text-primary-foreground hover:bg-primary-600 shadow-soft",
        secondary:
          "border border-border bg-surface-elevated text-ink hover:bg-surface dark:border-border-dark dark:bg-surface-dark-elevated dark:text-ink-dark dark:hover:bg-surface-dark",
        outline:
          "border border-border text-ink hover:bg-surface-elevated dark:border-border-dark dark:text-ink-dark dark:hover:bg-surface-dark-elevated",
        ghost:
          "text-ink hover:bg-surface-elevated/60 dark:text-ink-dark dark:hover:bg-surface-dark-elevated/60",
        destructive:
          "bg-danger-500 text-white hover:bg-danger-500/90",
        accent:
          "bg-accent-500 text-white hover:bg-accent-600",
        link: "text-primary-500 underline-offset-4 hover:underline",
      },
      size: {
        default: "min-h-11 h-10 px-4 text-sm sm:min-h-10",
        sm: "min-h-11 h-8 px-3 text-sm sm:min-h-8",
        md: "min-h-11 h-10 px-4 text-sm sm:min-h-10",
        lg: "min-h-11 h-12 px-6 text-base sm:min-h-12",
        icon: "size-11 min-h-11 min-w-11 p-0 sm:size-10 sm:min-h-10 sm:min-w-10",
        "icon-sm": "size-11 min-h-11 min-w-11 p-0 sm:size-8 sm:min-h-8 sm:min-w-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

type ButtonProps = ButtonPrimitive.Props &
  VariantProps<typeof buttonVariants> & {
    loading?: boolean;
  };

function Button({
  className,
  variant = "default",
  size = "default",
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const resolvedVariant = variant === "primary" ? "default" : variant;

  return (
    <ButtonPrimitive
      data-slot="button"
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={cn(
        buttonVariants({ variant: resolvedVariant, size, className }),
        loading && "[&>:not(.btn-spinner)]:invisible"
      )}
      {...props}
    >
      {loading ? (
        <Loader2
          className="btn-spinner absolute size-4 animate-spin text-primary-foreground"
          aria-hidden
        />
      ) : null}
      {children}
    </ButtonPrimitive>
  );
}

export { Button, buttonVariants };
