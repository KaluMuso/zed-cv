import * as React from "react";
import { Input as InputPrimitive } from "@base-ui/react/input";

import { cn } from "@/lib/utils";

function Input({
  className,
  type,
  "aria-invalid": ariaInvalid,
  ...props
}: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      aria-invalid={ariaInvalid}
      className={cn(
        "min-h-11 w-full min-w-0 rounded-md border border-border bg-surface-elevated px-4 py-2 text-base text-ink transition-colors duration-base ease-out-soft outline-none placeholder:text-ink-muted focus-visible:border-primary-500 focus-visible:shadow-ring disabled:cursor-not-allowed disabled:opacity-50 dark:border-border-dark dark:bg-surface-dark-elevated dark:text-ink-dark dark:placeholder:text-ink-dark-muted md:text-body",
        (ariaInvalid === true || ariaInvalid === "true") &&
          "border-danger-500 focus-visible:border-danger-500 focus-visible:shadow-none",
        className
      )}
      {...props}
    />
  );
}

function FieldHelper({
  children,
  id,
}: {
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <p
      id={id}
      className="mt-1.5 text-sm text-danger-500"
      role="alert"
    >
      {children}
    </p>
  );
}

export { Input, FieldHelper };
